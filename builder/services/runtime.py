from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ..models import PrototypeProject
from .generator import generate_streamlit_artifacts

MAX_RUNTIME_SECONDS = int(os.environ.get('MAX_RUNTIME_SECONDS', '3600'))
MAX_CONCURRENT_RUNTIMES = int(os.environ.get('MAX_CONCURRENT_RUNTIMES', '5'))
MAX_MEMORY_BYTES = int(os.environ.get('MAX_MEMORY_BYTES', str(512 * 1024 * 1024)))


class PrototypeRuntimeError(RuntimeError):
    pass


def _runtime_root() -> Path:
    root = settings.GENERATED_ROOT / '.runtime'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _metadata_path(project: PrototypeProject) -> Path:
    return _runtime_root() / f'{project.slug}.json'


def _log_path(project: PrototypeProject) -> Path:
    return _runtime_root() / f'{project.slug}.log'


def _process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _cleanup_metadata(project: PrototypeProject) -> None:
    metadata_path = _metadata_path(project)
    if metadata_path.exists():
        metadata_path.unlink()


def _load_metadata(project: PrototypeProject) -> dict | None:
    metadata_path = _metadata_path(project)
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        _cleanup_metadata(project)
        return None
    pid = metadata.get('pid')
    if not _process_alive(pid):
        _cleanup_metadata(project)
        return None
    return metadata


def _count_active_runtimes() -> int:
    runtime_root = _runtime_root()
    count = 0
    for meta_file in runtime_root.glob('*.json'):
        try:
            data = json.loads(meta_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue
        if _process_alive(data.get('pid')):
            count += 1
    return count


def get_project_runtime(project: PrototypeProject) -> dict | None:
    metadata = _load_metadata(project)
    if not metadata:
        return None
    started_at = metadata.get('started_at')
    if started_at and MAX_RUNTIME_SECONDS > 0:
        try:
            start_time = datetime.fromisoformat(started_at)
            elapsed = (timezone.now() - start_time).total_seconds()
            if elapsed > MAX_RUNTIME_SECONDS:
                stop_project_runtime(project)
                return None
        except (ValueError, TypeError):
            pass
    return {
        **metadata,
        'log_path': str(_log_path(project)),
    }


def _pick_port(max_attempts: int = 5) -> int:
    for _ in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = int(sock.getsockname()[1])
        # Double-bind verification: confirm port is still free
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as verify:
                verify.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise PrototypeRuntimeError('Could not find an available port after multiple attempts.')


def _streamlit_command(app_path: Path, port: int) -> list[str]:
    base_args = [
        'streamlit',
        'run',
        str(app_path),
        '--server.headless',
        'true',
        '--server.address',
        '127.0.0.1',
        '--server.port',
        str(port),
        '--browser.gatherUsageStats',
        'false',
    ]
    uv_path = shutil.which('uv')
    if uv_path:
        return [uv_path, 'run', '--with', 'streamlit>=1.44,<2.0', *base_args]
    return [sys.executable, '-m', *base_args]


def _wait_for_port(port: int, process: subprocess.Popen, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise PrototypeRuntimeError('Streamlit exited before the preview became available.')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            try:
                sock.connect(('127.0.0.1', port))
            except OSError:
                time.sleep(0.25)
                continue
            return
    raise PrototypeRuntimeError('Timed out waiting for the Streamlit preview to start.')


def _tail_log(project: PrototypeProject, max_lines: int = 20) -> str:
    log_path = _log_path(project)
    if not log_path.exists():
        return ''
    lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    return '\n'.join(lines[-max_lines:])


def _preexec_resource_limits() -> None:
    os.setsid()
    if MAX_MEMORY_BYTES > 0:
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))


def start_project_runtime(project: PrototypeProject) -> dict:
    stop_project_runtime(project)

    active = _count_active_runtimes()
    if active >= MAX_CONCURRENT_RUNTIMES:
        raise PrototypeRuntimeError(
            f'Concurrent runtime limit reached ({MAX_CONCURRENT_RUNTIMES}). Stop a running prototype first.'
        )

    generate_streamlit_artifacts(project)
    app_path = project.generated_dir / 'app.py'
    if not app_path.exists():
        raise PrototypeRuntimeError('The generated Streamlit app is missing. Generate the package first.')

    port = _pick_port()
    command = _streamlit_command(app_path, port)
    log_path = _log_path(project)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open('w', encoding='utf-8') as log_file:
        process = subprocess.Popen(
            command,
            cwd=project.generated_dir,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=_preexec_resource_limits,
        )

    try:
        _wait_for_port(port, process)
    except PrototypeRuntimeError as exc:
        stop_project_runtime(project)
        tail = _tail_log(project)
        if tail:
            raise PrototypeRuntimeError(f'{exc}\n\n{tail}') from exc
        raise

    metadata = {
        'pid': process.pid,
        'port': port,
        'started_at': timezone.now().isoformat(),
    }
    _metadata_path(project).write_text(json.dumps(metadata), encoding='utf-8')
    return metadata


def stop_project_runtime(project: PrototypeProject) -> bool:
    metadata_path = _metadata_path(project)
    if not metadata_path.exists():
        return False
    metadata = _load_metadata(project)
    if not metadata:
        _cleanup_metadata(project)
        return False

    pid = metadata.get('pid')
    if _process_alive(pid):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if not _process_alive(pid):
                break
            time.sleep(0.1)

        if _process_alive(pid):
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    _cleanup_metadata(project)
    return True

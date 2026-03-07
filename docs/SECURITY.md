# Security Model

## Runtime Isolation

Streamlit prototype subprocesses are spawned with the following safeguards:

- **Memory limit**: `RLIMIT_AS` capped at `MAX_MEMORY_BYTES` (default 512 MB) via `resource.setrlimit`.
- **Session isolation**: Each subprocess runs in its own process group (`os.setsid()`), enabling clean group-level termination.
- **Lifetime cap**: Runtimes exceeding `MAX_RUNTIME_SECONDS` (default 3600) are auto-killed on next status check.
- **Concurrency cap**: At most `MAX_CONCURRENT_RUNTIMES` (default 5) subprocesses may run simultaneously.

All limits are configurable via environment variables.

## Authorization Model

- Every view that accesses a `PrototypeProject` filters by `created_by=request.user`.
- Users who do not own a project receive a 404 response (not 403), preventing project slug enumeration.
- The dashboard only shows projects owned by the authenticated user.
- Artifact downloads require that `project.created_by` matches the requesting user.

## Production Settings

When `DJANGO_SETTINGS_MODULE=config.settings.production`:

- `SECRET_KEY` is required (startup fails if unset).
- `DEBUG` is always `False`.
- HSTS, secure cookies, CSRF cookie security, and SSL redirect are all enabled by default.
- `SECURE_PROXY_SSL_HEADER` is set for reverse proxy deployments.
- Static files are served via WhiteNoise with compressed manifest storage.

## Known Limitations

- Streamlit subprocesses run on the same host as the Django app. For stronger isolation, run prototypes in separate containers.
- `RLIMIT_AS` limits virtual memory, not resident memory. For hard RSS limits, use cgroups or container-level constraints.
- Port allocation uses double-bind verification but is not fully atomic; collisions are possible under extreme concurrency.
- No rate limiting is applied to prototype generation or runtime starts. Consider adding middleware or reverse proxy rate limits for public deployments.

from __future__ import annotations

import html
import json
import shutil
import textwrap
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ..models import GeneratedArtifact, ProjectTemplate, PrototypeProject
from .generator_profiles import (
    get_template_profile,
    get_theme_profile,
    render_config_toml,
)
from .generator_sections import (
    section_constants,
    section_css,
    section_dashboard,
    section_database,
    section_detail_screen,
    section_form_screen,
    section_helpers,
    section_imports,
    section_list_screen,
    section_main,
    section_navigation,
    section_rule_engine,
    section_screen_router,
)

STLITE_BROWSER_VERSION = "1.2.0"


def _build_theme_profile(template_kind: str) -> dict:
    return get_theme_profile(template_kind)


def build_project_spec(project: PrototypeProject) -> dict:
    workflow_states = list(
        project.workflow_states.order_by("order", "name").values(
            "name",
            "slug",
            "order",
            "is_initial",
            "is_terminal",
        )
    )

    entities = []
    for entity in project.entities.order_by("order", "name").prefetch_related("fields"):
        entities.append(
            {
                "name": entity.name,
                "plural_name": entity.plural_name,
                "slug": entity.slug,
                "description": entity.description,
                "fields": [
                    {
                        "name": field.name,
                        "label": field.label,
                        "field_type": field.field_type,
                        "required": field.required,
                        "help_text": field.help_text,
                        "include_in_list": field.include_in_list,
                        "is_calculated": field.is_calculated,
                        "calculation_expression": field.calculation_expression,
                        "visibility_condition": field.visibility_condition,
                        "validation_expression": field.validation_expression,
                        "validation_message": field.validation_message,
                        "choices": field.parsed_choices,
                        "related_entity": field.related_entity.slug
                        if field.related_entity
                        else None,
                    }
                    for field in entity.fields.order_by("order", "name")
                ],
            }
        )

    screens = [
        {
            "title": screen.title,
            "slug": screen.slug,
            "screen_type": screen.screen_type,
            "entity": screen.entity.slug if screen.entity else None,
            "include_in_navigation": screen.include_in_navigation,
        }
        for screen in project.screens.order_by("order", "title").select_related(
            "entity"
        )
    ]

    return {
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "template_kind": project.template_kind,
        "generated_at": timezone.now().isoformat(),
        "workflow_states": workflow_states,
        "entities": entities,
        "screens": screens,
    }


def generate_streamlit_artifacts(project: PrototypeProject) -> list[GeneratedArtifact]:
    project_dir = settings.GENERATED_ROOT / project.slug
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    archive_root = settings.GENERATED_ROOT / f"{project.slug}-streamlit-prototype"
    archive_file = archive_root.with_suffix(".zip")
    if archive_file.exists():
        archive_file.unlink()

    spec = build_project_spec(project)
    spec_path = project_dir / "prototype_spec.json"
    app_path = project_dir / "app.py"
    browser_preview_path = project_dir / "browser_preview.html"
    readme_path = project_dir / "README.md"
    requirements_path = project_dir / "requirements.txt"

    streamlit_dir = project_dir / ".streamlit"
    streamlit_dir.mkdir(exist_ok=True)
    config_path = streamlit_dir / "config.toml"

    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    app_path.write_text(render_streamlit_app(spec), encoding="utf-8")
    browser_preview_path.write_text(render_browser_preview(spec), encoding="utf-8")
    readme_path.write_text(render_readme(spec), encoding="utf-8")
    requirements_path.write_text("streamlit>=1.44,<2.0\n", encoding="utf-8")
    config_path.write_text(render_config_toml(spec), encoding="utf-8")

    archive_path = Path(
        shutil.make_archive(
            base_name=str(archive_root),
            format="zip",
            root_dir=project_dir,
        )
    )

    project.artifacts.all().delete()
    artifacts = [
        ("app", app_path),
        ("spec", spec_path),
        ("preview", browser_preview_path),
        ("readme", readme_path),
        ("requirements", requirements_path),
        ("config", config_path),
        ("zip", archive_path),
    ]
    created_artifacts = [
        GeneratedArtifact.objects.create(
            project=project,
            artifact_type=artifact_type,
            relative_path=str(path.relative_to(settings.GENERATED_ROOT)),
        )
        for artifact_type, path in artifacts
    ]
    project.latest_generation_at = timezone.now()
    project.save(update_fields=["latest_generation_at", "updated_at"])
    return created_artifacts


def render_readme(spec: dict) -> str:
    return textwrap.dedent(
        f"""\
        # {spec["name"]} Streamlit Prototype

        This package was generated by Prototype Studio from the saved project spec.

        ## Run locally

        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        streamlit run app.py
        ```

        ## What is included

        - `app.py`: the generated Streamlit prototype
        - `prototype_spec.json`: the schema exported from the Django builder
        - `prototype.db`: created automatically on first run

        ## Screens

        {chr(10).join(f"- {screen['title']} ({screen['screen_type']})" for screen in spec["screens"]) or "- No screens defined yet"}
        """
    )


def render_streamlit_app(spec: dict) -> str:
    return render_streamlit_app_with_options(spec)


def render_streamlit_app_with_options(
    spec: dict,
    *,
    db_path_expression: str | None = None,
) -> str:
    kind = spec.get("template_kind", ProjectTemplate.BLANK)
    theme = get_theme_profile(kind)
    profile = get_template_profile(kind)
    sections = [
        section_imports(),
        section_constants(
            spec,
            theme,
            profile,
            db_path_expression=db_path_expression,
        ),
        section_database(),
        section_rule_engine(),
        section_helpers(),
        section_navigation(spec, profile),
        section_dashboard(spec, theme, profile),
        section_list_screen(spec, theme, profile),
        section_detail_screen(spec, theme, profile),
        section_form_screen(spec, theme, profile),
        section_screen_router(),
        section_css(theme, profile),
        section_main(spec, profile),
    ]
    return "\n\n".join(sections)


def _json_script_value(value: object) -> str:
    return json.dumps(value, indent=2).replace("</", "<\\/")


def render_browser_preview(spec: dict) -> str:
    app_source = render_streamlit_app(spec)
    files = {
        "/app/app.py": app_source,
        "/app/prototype_spec.json": json.dumps(spec, indent=2),
        "/app/README.md": render_readme(spec),
        "/app/.streamlit/config.toml": render_config_toml(spec),
    }
    title = html.escape(f"{spec['name']} Browser Prototype")
    return textwrap.dedent(
        f"""\
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>{title}</title>
            <link
              rel="stylesheet"
              href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE_BROWSER_VERSION}/build/stlite.css"
            />
            <style>
              html, body {{
                margin: 0;
                min-height: 100%;
                background: #f2f4f1;
                color: #16211b;
                font-family: sans-serif;
              }}

              body {{
                display: flex;
                flex-direction: column;
              }}

              .preview-shell {{
                padding: 14px 18px;
                border-bottom: 1px solid rgba(22, 33, 27, 0.12);
                background: linear-gradient(135deg, #17362d 0%, #5f877a 100%);
                color: #f7fbf9;
              }}

              .preview-shell strong {{
                display: block;
                font-size: 1rem;
              }}

              .preview-shell span {{
                display: block;
                margin-top: 4px;
                font-size: 0.85rem;
                opacity: 0.84;
              }}

              #root {{
                flex: 1;
                min-height: calc(100vh - 74px);
              }}
            </style>
          </head>
          <body>
            <div class="preview-shell">
              <strong>{title}</strong>
              <span>Runs fully in this browser. Prototype data resets when this page reloads.</span>
            </div>
            <div id="root"></div>
            <script type="module">
              import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE_BROWSER_VERSION}/build/stlite.js";

              const files = {_json_script_value(files)};
              const root = document.getElementById("root");

              mount(
                {{
                  entrypoint: "/app/app.py",
                  files,
                  streamlitConfig: {{
                    "client.toolbarMode": "viewer",
                  }},
                }},
                root,
              );
            </script>
          </body>
        </html>
        """
    )

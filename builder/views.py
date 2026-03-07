from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .auth import get_project_for_user, get_project_for_user_with_prefetch
from .forms import (
    EntityForm,
    FieldForm,
    ProjectForm,
    ScreenDefinitionForm,
    WorkflowStateForm,
)
from .models import (
    EntityDefinition,
    FieldDefinition,
    GeneratedArtifact,
    PrototypeProject,
    ScreenDefinition,
    WorkflowState,
)
from .services.generator import build_project_spec, generate_streamlit_artifacts
from .services.preview import build_project_preview
from .services.runtime import (
    PrototypeRuntimeError,
    get_project_runtime,
    start_project_runtime,
    stop_project_runtime,
)
from .services.templates import seed_project_from_template


RAILWAY_RUNTIME_UNAVAILABLE_MESSAGE = (
    "Live prototype preview is unavailable on Railway. Generate the package here "
    "and run the exported Streamlit app locally."
)

BROWSER_PREVIEW_MESSAGE = (
    "Browser prototype runs fully in this browser. Prototype data persists in "
    "this browser only."
)


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _move_ordered_instance(instance, queryset, direction: str) -> bool:
    if direction not in {"up", "down"}:
        return False
    siblings = queryset.exclude(pk=instance.pk)
    if direction == "up":
        neighbor = (
            siblings.filter(order__lt=instance.order).order_by("-order", "-pk").first()
        )
    else:
        neighbor = (
            siblings.filter(order__gt=instance.order).order_by("order", "pk").first()
        )
    if not neighbor:
        return False
    current_order = instance.order
    instance.__class__.objects.filter(pk=instance.pk).update(order=neighbor.order)
    neighbor.__class__.objects.filter(pk=neighbor.pk).update(order=current_order)
    return True


def _normalize_order(queryset) -> None:
    ordered = list(queryset.order_by("order", "pk"))
    for index, instance in enumerate(ordered, start=1):
        if instance.order != index:
            instance.__class__.objects.filter(pk=instance.pk).update(order=index)


def _build_rule_builder_config(
    entity: EntityDefinition, editing_field: FieldDefinition | None = None
) -> dict:
    return {
        "fields": [
            {
                "name": field.name,
                "label": field.label,
                "field_type": field.field_type,
                "choices": field.parsed_choices,
            }
            for field in entity.fields.order_by("order", "name")
            if not editing_field or field.pk != editing_field.pk
        ],
    }


def _entity_detail_context(
    project: PrototypeProject,
    entity: EntityDefinition,
    field_form: FieldForm,
    field_edit_target: FieldDefinition | None,
) -> dict:
    effective_edit_target = field_edit_target or (
        field_form.instance if field_form.instance.pk else None
    )
    return {
        "project": project,
        "entity": entity,
        "field_form": field_form,
        "field_form_action": (
            reverse(
                "field-update",
                kwargs={
                    "slug": project.slug,
                    "entity_slug": entity.slug,
                    "field_id": effective_edit_target.pk,
                },
            )
            if effective_edit_target
            else reverse(
                "field-add", kwargs={"slug": project.slug, "entity_slug": entity.slug}
            )
        ),
        "field_edit_target": effective_edit_target,
        "rule_builder_config": _build_rule_builder_config(
            entity, effective_edit_target
        ),
    }


def _project_detail_context(
    project: PrototypeProject,
    request: HttpRequest,
    *,
    entity_form: EntityForm | None = None,
    state_form: WorkflowStateForm | None = None,
    screen_form: ScreenDefinitionForm | None = None,
) -> dict:
    entity_edit_target = (
        project.entities.filter(slug=request.GET.get("edit_entity")).first()
        if request.GET.get("edit_entity")
        else None
    )
    state_edit_target = project.workflow_states.filter(
        pk=_parse_int(request.GET.get("edit_state"))
    ).first()
    screen_edit_target = (
        project.screens.filter(pk=_parse_int(request.GET.get("edit_screen")))
        .select_related("entity")
        .first()
    )

    if entity_form is None:
        entity_form = (
            EntityForm(instance=entity_edit_target)
            if entity_edit_target
            else EntityForm()
        )
    if state_form is None:
        state_form = (
            WorkflowStateForm(instance=state_edit_target)
            if state_edit_target
            else WorkflowStateForm()
        )
    if screen_form is None:
        screen_form = (
            ScreenDefinitionForm(instance=screen_edit_target, project=project)
            if screen_edit_target
            else ScreenDefinitionForm(project=project)
        )

    return {
        "project": project,
        "entity_form": entity_form,
        "entity_form_action": (
            reverse(
                "entity-update",
                kwargs={"slug": project.slug, "entity_slug": entity_edit_target.slug},
            )
            if entity_edit_target
            else reverse("entity-add", kwargs={"slug": project.slug})
        ),
        "entity_edit_target": entity_edit_target,
        "state_form": state_form,
        "state_form_action": (
            reverse(
                "state-update",
                kwargs={"slug": project.slug, "state_id": state_edit_target.pk},
            )
            if state_edit_target
            else reverse("state-add", kwargs={"slug": project.slug})
        ),
        "state_edit_target": state_edit_target,
        "screen_form": screen_form,
        "screen_form_action": (
            reverse(
                "screen-update",
                kwargs={"slug": project.slug, "screen_id": screen_edit_target.pk},
            )
            if screen_edit_target
            else reverse("screen-add", kwargs={"slug": project.slug})
        ),
        "screen_edit_target": screen_edit_target,
        **_browser_preview_context(project),
        **_prototype_runtime_context(project, request),
    }


def _browser_preview_context(project: PrototypeProject) -> dict:
    return {
        "browser_preview_url": reverse(
            "project-browser-preview", kwargs={"slug": project.slug}
        ),
        "browser_preview_message": BROWSER_PREVIEW_MESSAGE,
    }


def _prototype_runtime_context(project: PrototypeProject, request: HttpRequest) -> dict:
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return {
            "prototype_runtime": None,
            "prototype_runtime_supported": False,
            "prototype_runtime_unavailable_reason": RAILWAY_RUNTIME_UNAVAILABLE_MESSAGE,
        }
    runtime = get_project_runtime(project)
    if not runtime:
        return {
            "prototype_runtime": None,
            "prototype_runtime_supported": True,
            "prototype_runtime_unavailable_reason": "",
        }
    host = request.get_host().split(":", 1)[0]
    if host == "testserver":
        host = "127.0.0.1"
    return {
        "prototype_runtime": {
            **runtime,
            "url": f"http://{host}:{runtime['port']}",
        },
        "prototype_runtime_supported": True,
        "prototype_runtime_unavailable_reason": "",
    }


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    projects = list(
        PrototypeProject.objects.filter(created_by=request.user).prefetch_related(
            "entities", "workflow_states", "screens"
        )
    )
    return render(
        request,
        "builder/dashboard.html",
        {
            "projects": projects,
            "project_count": len(projects),
            "generated_count": sum(1 for project in projects if project.is_generated),
            "entity_total": sum(project.entities_count for project in projects),
        },
    )


@login_required
def project_create(request: HttpRequest) -> HttpResponse:
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.created_by = request.user
        project.save()
        seed_project_from_template(project)
        messages.success(request, f"Created {project.name}.")
        return redirect(project)
    return render(request, "builder/project_form.html", {"form": form})


@login_required
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request),
    )


@login_required
def entity_detail(request: HttpRequest, slug: str, entity_slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(
        EntityDefinition.objects.prefetch_related("fields", "screens"),
        project=project,
        slug=entity_slug,
    )
    field_edit_target = entity.fields.filter(
        pk=_parse_int(request.GET.get("edit_field"))
    ).first()
    field_form = (
        FieldForm(instance=field_edit_target, project=project, entity=entity)
        if field_edit_target
        else FieldForm(project=project, entity=entity)
    )
    return render(
        request,
        "builder/entity_detail.html",
        _entity_detail_context(project, entity, field_form, field_edit_target),
    )


@login_required
def add_entity(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    if request.method != "POST":
        return redirect(project)
    form = EntityForm(request.POST or None)
    if form.is_valid():
        entity = form.save(commit=False)
        entity.project = project
        entity.save()
        messages.success(request, f"Added entity {entity.name}.")
        return redirect(project)
    messages.error(
        request, "Could not add entity. Check the form values and try again."
    )
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, entity_form=form),
        status=400,
    )


@login_required
def update_entity(request: HttpRequest, slug: str, entity_slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    entity = get_object_or_404(EntityDefinition, project=project, slug=entity_slug)
    if request.method != "POST":
        return redirect(f"{project.get_absolute_url()}?edit_entity={entity.slug}")
    form = EntityForm(request.POST or None, instance=entity)
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated entity {entity.name}.")
        return redirect(project)
    messages.error(request, "Could not update entity. Check the values and try again.")
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, entity_form=form),
        status=400,
    )


@login_required
def delete_entity(request: HttpRequest, slug: str, entity_slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(EntityDefinition, project=project, slug=entity_slug)
    if request.method == "POST":
        entity_name = entity.name
        entity.delete()
        _normalize_order(project.entities.all())
        messages.success(request, f"Deleted entity {entity_name}.")
    return redirect(project)


@login_required
def move_entity(
    request: HttpRequest, slug: str, entity_slug: str, direction: str
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(EntityDefinition, project=project, slug=entity_slug)
    if request.method == "POST":
        moved = _move_ordered_instance(entity, project.entities.all(), direction)
        messages.success(
            request, f"Moved {entity.name} {direction}."
        ) if moved else messages.info(
            request,
            f"{entity.name} is already at the edge of the list.",
        )
    return redirect(project)


@login_required
def add_field(request: HttpRequest, slug: str, entity_slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(
        EntityDefinition.objects.prefetch_related("fields", "screens"),
        project=project,
        slug=entity_slug,
    )
    if request.method != "POST":
        return redirect(entity)
    form = FieldForm(request.POST or None, project=project, entity=entity)
    if form.is_valid():
        field = form.save(commit=False)
        field.entity = entity
        field.save()
        messages.success(request, f"Added field {field.label}.")
        return redirect(entity)
    messages.error(
        request, "Could not add field. Check the field type specific inputs."
    )
    return render(
        request,
        "builder/entity_detail.html",
        _entity_detail_context(project, entity, form, None),
        status=400,
    )


@login_required
def update_field(
    request: HttpRequest, slug: str, entity_slug: str, field_id: int
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(
        EntityDefinition.objects.prefetch_related("fields", "screens"),
        project=project,
        slug=entity_slug,
    )
    field = get_object_or_404(FieldDefinition, entity=entity, pk=field_id)
    if request.method != "POST":
        return redirect(f"{entity.get_absolute_url()}?edit_field={field.pk}")
    form = FieldForm(
        request.POST or None, instance=field, project=project, entity=entity
    )
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated field {field.label}.")
        return redirect(entity)
    messages.error(request, "Could not update field. Check the values and try again.")
    return render(
        request,
        "builder/entity_detail.html",
        _entity_detail_context(project, entity, form, field),
        status=400,
    )


@login_required
def delete_field(
    request: HttpRequest, slug: str, entity_slug: str, field_id: int
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(EntityDefinition, project=project, slug=entity_slug)
    field = get_object_or_404(FieldDefinition, entity=entity, pk=field_id)
    if request.method == "POST":
        field_label = field.label
        field.delete()
        _normalize_order(entity.fields.all())
        messages.success(request, f"Deleted field {field_label}.")
    return redirect(entity)


@login_required
def move_field(
    request: HttpRequest, slug: str, entity_slug: str, field_id: int, direction: str
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    entity = get_object_or_404(EntityDefinition, project=project, slug=entity_slug)
    field = get_object_or_404(FieldDefinition, entity=entity, pk=field_id)
    if request.method == "POST":
        moved = _move_ordered_instance(field, entity.fields.all(), direction)
        messages.success(
            request, f"Moved {field.label} {direction}."
        ) if moved else messages.info(
            request,
            f"{field.label} is already at the edge of the list.",
        )
    return redirect(entity)


@login_required
def add_workflow_state(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    if request.method != "POST":
        return redirect(project)
    form = WorkflowStateForm(request.POST or None)
    if form.is_valid():
        state = form.save(commit=False)
        state.project = project
        state.save()
        messages.success(request, f"Added workflow state {state.name}.")
        return redirect(project)
    messages.error(request, "Could not add workflow state.")
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, state_form=form),
        status=400,
    )


@login_required
def update_workflow_state(
    request: HttpRequest, slug: str, state_id: int
) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    state = get_object_or_404(WorkflowState, project=project, pk=state_id)
    if request.method != "POST":
        return redirect(f"{project.get_absolute_url()}?edit_state={state.pk}")
    form = WorkflowStateForm(request.POST or None, instance=state)
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated workflow state {state.name}.")
        return redirect(project)
    messages.error(request, "Could not update workflow state.")
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, state_form=form),
        status=400,
    )


@login_required
def delete_workflow_state(
    request: HttpRequest, slug: str, state_id: int
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    state = get_object_or_404(WorkflowState, project=project, pk=state_id)
    if request.method == "POST":
        state_name = state.name
        state.delete()
        _normalize_order(project.workflow_states.all())
        messages.success(request, f"Deleted workflow state {state_name}.")
    return redirect(project)


@login_required
def move_workflow_state(
    request: HttpRequest, slug: str, state_id: int, direction: str
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    state = get_object_or_404(WorkflowState, project=project, pk=state_id)
    if request.method == "POST":
        moved = _move_ordered_instance(state, project.workflow_states.all(), direction)
        messages.success(
            request, f"Moved {state.name} {direction}."
        ) if moved else messages.info(
            request,
            f"{state.name} is already at the edge of the list.",
        )
    return redirect(project)


@login_required
def add_screen(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    if request.method != "POST":
        return redirect(project)
    form = ScreenDefinitionForm(request.POST or None, project=project)
    if form.is_valid():
        screen = form.save(commit=False)
        screen.project = project
        screen.save()
        messages.success(request, f"Added screen {screen.title}.")
        return redirect(project)
    messages.error(request, "Could not add screen.")
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, screen_form=form),
        status=400,
    )


@login_required
def update_screen(request: HttpRequest, slug: str, screen_id: int) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    screen = get_object_or_404(ScreenDefinition, project=project, pk=screen_id)
    if request.method != "POST":
        return redirect(f"{project.get_absolute_url()}?edit_screen={screen.pk}")
    form = ScreenDefinitionForm(request.POST or None, instance=screen, project=project)
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated screen {screen.title}.")
        return redirect(project)
    messages.error(request, "Could not update screen.")
    return render(
        request,
        "builder/project_detail.html",
        _project_detail_context(project, request, screen_form=form),
        status=400,
    )


@login_required
def delete_screen(request: HttpRequest, slug: str, screen_id: int) -> HttpResponse:
    project = get_project_for_user(request, slug)
    screen = get_object_or_404(ScreenDefinition, project=project, pk=screen_id)
    if request.method == "POST":
        screen_title = screen.title
        screen.delete()
        _normalize_order(project.screens.all())
        messages.success(request, f"Deleted screen {screen_title}.")
    return redirect(project)


@login_required
def move_screen(
    request: HttpRequest, slug: str, screen_id: int, direction: str
) -> HttpResponse:
    project = get_project_for_user(request, slug)
    screen = get_object_or_404(ScreenDefinition, project=project, pk=screen_id)
    if request.method == "POST":
        moved = _move_ordered_instance(screen, project.screens.all(), direction)
        messages.success(
            request, f"Moved {screen.title} {direction}."
        ) if moved else messages.info(
            request,
            f"{screen.title} is already at the edge of the list.",
        )
    return redirect(project)


@login_required
def project_preview(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user_with_prefetch(
        request,
        slug,
        prefetch_related=[
            "entities__fields",
            "workflow_states",
            "screens__entity",
            "artifacts",
        ],
    )
    spec = build_project_spec(project)
    preview_context = build_project_preview(spec, request.GET.get("screen"))
    return render(
        request,
        "builder/project_preview.html",
        {
            "project": project,
            "spec": spec,
            **_browser_preview_context(project),
            **_prototype_runtime_context(project, request),
            **preview_context,
        },
    )


@login_required
def project_browser_preview(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    generate_streamlit_artifacts(project)
    preview_path = project.generated_dir / "browser_preview.html"
    if not preview_path.exists():
        raise Http404("Browser preview is unavailable.")
    response = HttpResponse(
        preview_path.read_text(encoding="utf-8"),
        content_type="text/html; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    return response


@login_required
def generate_project(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    if request.method != "POST":
        return redirect(project)
    artifacts = generate_streamlit_artifacts(project)
    messages.success(request, f"Generated {len(artifacts)} Streamlit artifacts.")
    return redirect(project)


@login_required
def run_project(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    if request.method != "POST":
        return redirect(project)
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        messages.info(request, RAILWAY_RUNTIME_UNAVAILABLE_MESSAGE)
        return redirect(project)
    try:
        runtime = start_project_runtime(project)
    except PrototypeRuntimeError as exc:
        messages.error(request, f"Could not start prototype preview. {exc}")
        return redirect(project)
    messages.success(
        request, f"Prototype preview is running on port {runtime['port']}."
    )
    return redirect(project)


@login_required
def stop_project(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_project_for_user(request, slug)
    if request.method != "POST":
        return redirect(project)
    if stop_project_runtime(project):
        messages.success(request, "Stopped the running prototype preview.")
    else:
        messages.info(request, "No running prototype preview was found.")
    return redirect(project)


@login_required
def download_artifact(request: HttpRequest, artifact_id: int) -> FileResponse:
    artifact = get_object_or_404(
        GeneratedArtifact.objects.select_related("project"),
        pk=artifact_id,
        project__created_by=request.user,
    )
    generated_root = settings.GENERATED_ROOT.resolve()
    artifact_path = (settings.GENERATED_ROOT / artifact.relative_path).resolve()
    if generated_root not in artifact_path.parents and artifact_path != generated_root:
        raise Http404("Invalid artifact path.")
    if not artifact_path.exists():
        raise Http404("Artifact no longer exists.")
    return FileResponse(
        artifact_path.open("rb"),
        as_attachment=True,
        filename=Path(artifact.relative_path).name,
    )

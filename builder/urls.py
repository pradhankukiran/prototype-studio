from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.home, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("projects/new/", views.project_create, name="project-create"),
    path("projects/<slug:slug>/", views.project_detail, name="project-detail"),
    path(
        "projects/<slug:slug>/preview/", views.project_preview, name="project-preview"
    ),
    path(
        "projects/<slug:slug>/generate/",
        views.generate_project,
        name="project-generate",
    ),
    path(
        "projects/<slug:slug>/browser-preview/",
        views.project_browser_preview,
        name="project-browser-preview",
    ),
    path("projects/<slug:slug>/run/", views.run_project, name="project-run"),
    path("projects/<slug:slug>/stop/", views.stop_project, name="project-stop"),
    path("projects/<slug:slug>/entities/add/", views.add_entity, name="entity-add"),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/update/",
        views.update_entity,
        name="entity-update",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/delete/",
        views.delete_entity,
        name="entity-delete",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/move/<str:direction>/",
        views.move_entity,
        name="entity-move",
    ),
    path(
        "projects/<slug:slug>/states/add/", views.add_workflow_state, name="state-add"
    ),
    path(
        "projects/<slug:slug>/states/<int:state_id>/update/",
        views.update_workflow_state,
        name="state-update",
    ),
    path(
        "projects/<slug:slug>/states/<int:state_id>/delete/",
        views.delete_workflow_state,
        name="state-delete",
    ),
    path(
        "projects/<slug:slug>/states/<int:state_id>/move/<str:direction>/",
        views.move_workflow_state,
        name="state-move",
    ),
    path("projects/<slug:slug>/screens/add/", views.add_screen, name="screen-add"),
    path(
        "projects/<slug:slug>/screens/<int:screen_id>/update/",
        views.update_screen,
        name="screen-update",
    ),
    path(
        "projects/<slug:slug>/screens/<int:screen_id>/delete/",
        views.delete_screen,
        name="screen-delete",
    ),
    path(
        "projects/<slug:slug>/screens/<int:screen_id>/move/<str:direction>/",
        views.move_screen,
        name="screen-move",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/",
        views.entity_detail,
        name="entity-detail",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/fields/add/",
        views.add_field,
        name="field-add",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/fields/<int:field_id>/update/",
        views.update_field,
        name="field-update",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/fields/<int:field_id>/delete/",
        views.delete_field,
        name="field-delete",
    ),
    path(
        "projects/<slug:slug>/entities/<slug:entity_slug>/fields/<int:field_id>/move/<str:direction>/",
        views.move_field,
        name="field-move",
    ),
    path(
        "artifacts/<int:artifact_id>/download/",
        views.download_artifact,
        name="artifact-download",
    ),
]

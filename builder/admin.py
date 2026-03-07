from django.contrib import admin

from .models import (
    EntityDefinition,
    FieldDefinition,
    GeneratedArtifact,
    PrototypeProject,
    ScreenDefinition,
    WorkflowState,
)


class FieldDefinitionInline(admin.TabularInline):
    model = FieldDefinition
    fk_name = "entity"
    extra = 0


@admin.register(EntityDefinition)
class EntityDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "order")
    list_filter = ("project",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FieldDefinitionInline]


@admin.register(PrototypeProject)
class PrototypeProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "template_kind",
        "created_by",
        "updated_at",
        "latest_generation_at",
    )
    list_filter = ("template_kind",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FieldDefinition)
class FieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "entity", "field_type", "required", "order")
    list_filter = ("field_type", "required", "entity__project")
    search_fields = ("name", "label", "entity__name")


@admin.register(WorkflowState)
class WorkflowStateAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "order", "is_initial", "is_terminal")
    list_filter = ("project", "is_initial", "is_terminal")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ScreenDefinition)
class ScreenDefinitionAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "screen_type", "entity", "order")
    list_filter = ("screen_type", "project")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(GeneratedArtifact)
class GeneratedArtifactAdmin(admin.ModelAdmin):
    list_display = ("artifact_type", "project", "relative_path", "created_at")
    list_filter = ("artifact_type", "project")


# Register your models here.

from __future__ import annotations

from django import forms

from .models import (
    EntityDefinition,
    FieldDefinition,
    PrototypeProject,
    ScreenDefinition,
    WorkflowState,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = f"{css_class} checkbox-input".strip()
            else:
                widget.attrs["class"] = f"{css_class} form-input".strip()


class ProjectForm(StyledModelForm):
    class Meta:
        model = PrototypeProject
        fields = ["name", "description", "template_kind"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class EntityForm(StyledModelForm):
    class Meta:
        model = EntityDefinition
        fields = ["name", "plural_name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class FieldForm(StyledModelForm):
    class Meta:
        model = FieldDefinition
        fields = [
            "name",
            "label",
            "field_type",
            "required",
            "help_text",
            "include_in_list",
            "is_calculated",
            "calculation_expression",
            "visibility_condition",
            "validation_expression",
            "validation_message",
            "choices_text",
            "related_entity",
        ]
        widgets = {
            "calculation_expression": forms.Textarea(attrs={"rows": 2}),
            "visibility_condition": forms.Textarea(attrs={"rows": 2}),
            "validation_expression": forms.Textarea(attrs={"rows": 2}),
            "choices_text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, project=None, entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if entity is not None:
            self.instance.entity = entity
        queryset = EntityDefinition.objects.none()
        if project is not None:
            queryset = project.entities.order_by("order", "name")
        self.fields["related_entity"].queryset = queryset
        self.fields[
            "calculation_expression"
        ].help_text = "Example: weekly_hours * hourly_rate"
        self.fields[
            "visibility_condition"
        ].help_text = 'Example: service_type == "Transport"'
        self.fields[
            "validation_expression"
        ].help_text = "Example: value >= 0 and value <= plan_budget"
        self.fields[
            "validation_message"
        ].help_text = "Shown when the validation expression returns false."


class WorkflowStateForm(StyledModelForm):
    class Meta:
        model = WorkflowState
        fields = ["name", "is_initial", "is_terminal"]


class ScreenDefinitionForm(StyledModelForm):
    class Meta:
        model = ScreenDefinition
        fields = ["title", "screen_type", "entity", "include_in_navigation"]

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = EntityDefinition.objects.none()
        if project is not None:
            queryset = project.entities.order_by("order", "name")
        self.fields["entity"].queryset = queryset

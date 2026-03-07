from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .services.rules import RuleExpressionError, validate_rule_expression

User = get_user_model()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ProjectTemplate(models.TextChoices):
    BLANK = 'blank', 'Blank workspace'
    QUOTE_BUILDER = 'quote_builder', 'Quote builder'
    CRM = 'crm', 'CRM'
    APPROVAL_FLOW = 'approval_flow', 'Approval workflow'
    CASE_TRACKER = 'case_tracker', 'Case tracker'


class PrototypeProject(TimestampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    template_kind = models.CharField(
        max_length=32,
        choices=ProjectTemplate.choices,
        default=ProjectTemplate.BLANK,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='prototype_projects',
        null=True,
        blank=True,
    )
    latest_generation_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at', 'name']
        indexes = [
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('project-detail', kwargs={'slug': self.slug})

    @property
    def generated_dir(self) -> Path:
        return settings.GENERATED_ROOT / self.slug

    def _related_count(self, relation_name: str) -> int:
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if relation_name in prefetched:
            return len(prefetched[relation_name])
        return getattr(self, relation_name).count()

    @property
    def is_generated(self) -> bool:
        return self.latest_generation_at is not None

    @property
    def readiness_checks(self) -> list[tuple[str, bool]]:
        return [
            ('Entities modelled', self._related_count('entities') > 0),
            ('Workflow defined', self._related_count('workflow_states') > 0),
            ('Screens mapped', self._related_count('screens') > 0),
            ('Prototype exported', self.is_generated),
        ]

    @property
    def completion_percent(self) -> int:
        checks = self.readiness_checks
        return int((sum(1 for _, is_done in checks if is_done) / len(checks)) * 100)

    @property
    def status_label(self) -> str:
        if self.completion_percent == 100:
            return 'Ready'
        if self.completion_percent >= 50:
            return 'In build'
        return 'Draft'

    @property
    def entities_count(self) -> int:
        return self._related_count('entities')

    @property
    def workflow_states_count(self) -> int:
        return self._related_count('workflow_states')

    @property
    def screens_count(self) -> int:
        return self._related_count('screens')

    @property
    def artifacts_count(self) -> int:
        return self._related_count('artifacts')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self) -> str:
        base_slug = slugify(self.name) or 'prototype-project'
        slug = base_slug
        counter = 2
        while PrototypeProject.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        return slug


class EntityDefinition(TimestampedModel):
    project = models.ForeignKey(
        PrototypeProject,
        on_delete=models.CASCADE,
        related_name='entities',
    )
    name = models.CharField(max_length=80)
    plural_name = models.CharField(max_length=80, blank=True)
    slug = models.SlugField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['project', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['project', 'slug'], name='uniq_entity_slug_per_project'),
        ]

    def __str__(self) -> str:
        return f'{self.project.name}: {self.name}'

    def get_absolute_url(self) -> str:
        return reverse(
            'entity-detail',
            kwargs={'slug': self.project.slug, 'entity_slug': self.slug},
        )

    @property
    def field_count(self) -> int:
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if 'fields' in prefetched:
            return len(prefetched['fields'])
        return self.fields.count()

    @property
    def screen_count(self) -> int:
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if 'screens' in prefetched:
            return len(prefetched['screens'])
        return self.screens.count()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.plural_name:
            self.plural_name = f'{self.name}s'
        if not self.order:
            max_order = (
                EntityDefinition.objects.filter(project=self.project).exclude(pk=self.pk)
                .aggregate(models.Max('order'))
                .get('order__max')
                or 0
            )
            self.order = max_order + 1
        super().save(*args, **kwargs)


class FieldType(models.TextChoices):
    SHORT_TEXT = 'short_text', 'Short text'
    LONG_TEXT = 'long_text', 'Long text'
    INTEGER = 'integer', 'Integer'
    DECIMAL = 'decimal', 'Decimal'
    DATE = 'date', 'Date'
    BOOLEAN = 'boolean', 'Boolean'
    CHOICE = 'choice', 'Choice'
    RELATION = 'relation', 'Relation'


class FieldDefinition(TimestampedModel):
    entity = models.ForeignKey(
        EntityDefinition,
        on_delete=models.CASCADE,
        related_name='fields',
    )
    name = models.CharField(max_length=80)
    label = models.CharField(max_length=80, blank=True)
    field_type = models.CharField(max_length=24, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=160, blank=True)
    order = models.PositiveIntegerField(default=0)
    include_in_list = models.BooleanField(default=True)
    is_calculated = models.BooleanField(default=False)
    calculation_expression = models.TextField(blank=True)
    visibility_condition = models.TextField(blank=True)
    validation_expression = models.TextField(blank=True)
    validation_message = models.CharField(max_length=160, blank=True)
    choices_text = models.TextField(blank=True)
    related_entity = models.ForeignKey(
        EntityDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_fields',
    )

    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['entity', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['entity', 'name'], name='uniq_field_name_per_entity'),
        ]

    def __str__(self) -> str:
        return f'{self.entity.name}: {self.name}'

    @property
    def parsed_choices(self) -> list[str]:
        return [choice.strip() for choice in self.choices_text.splitlines() if choice.strip()]

    @property
    def has_rules(self) -> bool:
        return bool(
            self.is_calculated
            or self.visibility_condition
            or self.validation_expression
        )

    def clean(self):
        super().clean()
        if self.field_type == FieldType.CHOICE and not self.parsed_choices:
            raise ValidationError({'choices_text': 'Add one option per line for choice fields.'})
        if self.field_type == FieldType.RELATION:
            if not self.related_entity:
                raise ValidationError({'related_entity': 'Select the related entity for relation fields.'})
            if self.related_entity.project_id != self.entity.project_id:
                raise ValidationError({'related_entity': 'Relation targets must be in the same project.'})
        if self.is_calculated and not self.calculation_expression.strip():
            raise ValidationError({'calculation_expression': 'Add an expression for calculated fields.'})
        if self.calculation_expression.strip() and not self.is_calculated:
            raise ValidationError({'is_calculated': 'Enable calculated field mode to use a calculation expression.'})
        if self.validation_message and not self.validation_expression.strip():
            raise ValidationError({'validation_expression': 'Add a validation expression or clear the message.'})
        for field_name in ('calculation_expression', 'visibility_condition', 'validation_expression'):
            expression = getattr(self, field_name).strip()
            if not expression:
                continue
            try:
                validate_rule_expression(expression)
            except RuleExpressionError as exc:
                raise ValidationError({field_name: str(exc)}) from exc

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.name.replace('_', ' ').title()
        if not self.order:
            max_order = (
                FieldDefinition.objects.filter(entity=self.entity).exclude(pk=self.pk)
                .aggregate(models.Max('order'))
                .get('order__max')
                or 0
            )
            self.order = max_order + 1
        super().save(*args, **kwargs)


class WorkflowState(TimestampedModel):
    project = models.ForeignKey(
        PrototypeProject,
        on_delete=models.CASCADE,
        related_name='workflow_states',
    )
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=80, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['project', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['project', 'slug'], name='uniq_workflow_slug_per_project'),
        ]

    def __str__(self) -> str:
        return f'{self.project.name}: {self.name}'

    def clean(self):
        super().clean()
        existing_initial = WorkflowState.objects.filter(project=self.project, is_initial=True).exclude(pk=self.pk)
        if self.is_initial and existing_initial.exists():
            raise ValidationError({'is_initial': 'Only one initial state is allowed per project.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.order:
            max_order = (
                WorkflowState.objects.filter(project=self.project).exclude(pk=self.pk)
                .aggregate(models.Max('order'))
                .get('order__max')
                or 0
            )
            self.order = max_order + 1
        super().save(*args, **kwargs)


class ScreenType(models.TextChoices):
    DASHBOARD = 'dashboard', 'Dashboard'
    LIST = 'list', 'List'
    FORM = 'form', 'Form'
    DETAIL = 'detail', 'Detail'


class ScreenDefinition(TimestampedModel):
    project = models.ForeignKey(
        PrototypeProject,
        on_delete=models.CASCADE,
        related_name='screens',
    )
    title = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, blank=True)
    screen_type = models.CharField(max_length=20, choices=ScreenType.choices)
    entity = models.ForeignKey(
        EntityDefinition,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='screens',
    )
    order = models.PositiveIntegerField(default=0)
    include_in_navigation = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'title']
        indexes = [
            models.Index(fields=['project', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['project', 'slug'], name='uniq_screen_slug_per_project'),
        ]

    def __str__(self) -> str:
        return f'{self.project.name}: {self.title}'

    def clean(self):
        super().clean()
        if self.screen_type != ScreenType.DASHBOARD and not self.entity:
            raise ValidationError({'entity': 'Select an entity for list, form, and detail screens.'})
        if self.entity and self.project_id and self.entity.project_id != self.project_id:
            raise ValidationError({'entity': 'Screens can only target entities in the same project.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.order:
            max_order = (
                ScreenDefinition.objects.filter(project=self.project).exclude(pk=self.pk)
                .aggregate(models.Max('order'))
                .get('order__max')
                or 0
            )
            self.order = max_order + 1
        super().save(*args, **kwargs)


class GeneratedArtifact(models.Model):
    project = models.ForeignKey(
        PrototypeProject,
        on_delete=models.CASCADE,
        related_name='artifacts',
    )
    artifact_type = models.CharField(max_length=40)
    relative_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['relative_path']
        indexes = [
            models.Index(fields=['project', 'artifact_type']),
        ]

    def __str__(self) -> str:
        return f'{self.project.name}: {self.relative_path}'

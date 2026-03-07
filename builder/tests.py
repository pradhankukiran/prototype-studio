from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import EntityDefinition, FieldDefinition, FieldType, ProjectTemplate, PrototypeProject, ScreenDefinition, ScreenType, WorkflowState
from .services.generator import build_project_spec, generate_streamlit_artifacts
from .services.preview import build_project_preview
from .services.rules import RuleExpressionError, evaluate_rule_expression, validate_rule_expression
from .services.templates import seed_project_from_template

User = get_user_model()


class TemplateSeedingTests(TestCase):
    def test_quote_builder_template_seeds_entities_screens_and_states(self):
        project = PrototypeProject.objects.create(
            name='LVC Quote Builder',
            template_kind=ProjectTemplate.QUOTE_BUILDER,
        )

        seed_project_from_template(project)

        self.assertEqual(project.entities.count(), 4)
        self.assertEqual(project.workflow_states.count(), 3)
        self.assertEqual(project.screens.count(), 7)
        quote_entity = project.entities.get(slug='quote')
        self.assertGreaterEqual(quote_entity.fields.count(), 4)


class GeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='demo', password='demo-pass-123')

    def test_build_project_spec_contains_expected_shape(self):
        project = PrototypeProject.objects.create(
            name='Ops CRM',
            created_by=self.user,
            template_kind=ProjectTemplate.CRM,
        )
        seed_project_from_template(project)

        spec = build_project_spec(project)

        self.assertEqual(spec['name'], 'Ops CRM')
        self.assertEqual(len(spec['entities']), 3)
        self.assertTrue(any(screen['screen_type'] == 'dashboard' for screen in spec['screens']))

    def test_build_project_spec_includes_rule_metadata(self):
        project = PrototypeProject.objects.create(
            name='Rule Studio',
            created_by=self.user,
            template_kind=ProjectTemplate.BLANK,
        )
        entity = EntityDefinition.objects.create(project=project, name='Quote', plural_name='Quotes', order=1)
        FieldDefinition.objects.create(
            entity=entity,
            name='hourly_rate',
            label='Hourly rate',
            field_type=FieldType.DECIMAL,
            order=1,
        )
        FieldDefinition.objects.create(
            entity=entity,
            name='weekly_hours',
            label='Weekly hours',
            field_type=FieldType.DECIMAL,
            order=2,
        )
        FieldDefinition.objects.create(
            entity=entity,
            name='total_value',
            label='Total value',
            field_type=FieldType.DECIMAL,
            order=3,
            is_calculated=True,
            calculation_expression='weekly_hours * hourly_rate',
            visibility_condition='hourly_rate > 0',
            validation_expression='value >= 0',
            validation_message='Total must stay positive',
        )

        spec = build_project_spec(project)

        field_spec = spec['entities'][0]['fields'][2]
        self.assertTrue(field_spec['is_calculated'])
        self.assertEqual(field_spec['calculation_expression'], 'weekly_hours * hourly_rate')
        self.assertEqual(field_spec['visibility_condition'], 'hourly_rate > 0')
        self.assertEqual(field_spec['validation_expression'], 'value >= 0')
        self.assertEqual(field_spec['validation_message'], 'Total must stay positive')

    def test_generate_streamlit_artifacts_writes_files(self):
        project = PrototypeProject.objects.create(
            name='Case Control',
            created_by=self.user,
            template_kind=ProjectTemplate.CASE_TRACKER,
        )
        seed_project_from_template(project)

        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(GENERATED_ROOT=Path(temp_dir)):
                artifacts = generate_streamlit_artifacts(project)
                app_artifact = next(artifact for artifact in artifacts if artifact.artifact_type == 'app')
                app_source = (Path(temp_dir) / app_artifact.relative_path).read_text(encoding='utf-8')

        self.assertEqual(len(artifacts), 6)
        artifact_types = {artifact.artifact_type for artifact in artifacts}
        self.assertEqual(artifact_types, {'app', 'spec', 'readme', 'requirements', 'config', 'zip'})
        compile(app_source, str(Path(temp_dir) / app_artifact.relative_path), 'exec')


class RuleExpressionTests(TestCase):
    def test_rule_expression_supports_business_math(self):
        result = evaluate_rule_expression(
            'weekly_hours * hourly_rate if weekly_hours > 0 else 0',
            {'weekly_hours': 6, 'hourly_rate': 62.5},
        )

        self.assertEqual(result, 375.0)

    def test_rule_expression_rejects_unsafe_nodes(self):
        with self.assertRaises(RuleExpressionError):
            validate_rule_expression('quote.total')

    def test_preview_marks_calculated_and_conditional_fields(self):
        spec = {
            'workflow_states': [{'name': 'Draft', 'is_initial': True, 'is_terminal': False}],
            'entities': [
                {
                    'name': 'Quote',
                    'plural_name': 'Quotes',
                    'slug': 'quote',
                    'description': '',
                    'fields': [
                        {
                            'name': 'service_type',
                            'label': 'Service type',
                            'field_type': 'choice',
                            'required': False,
                            'help_text': '',
                            'include_in_list': True,
                            'choices': ['Standard', 'Transport'],
                            'related_entity': None,
                            'is_calculated': False,
                            'calculation_expression': '',
                            'visibility_condition': '',
                            'validation_expression': '',
                            'validation_message': '',
                        },
                        {
                            'name': 'travel_total',
                            'label': 'Travel total',
                            'field_type': 'decimal',
                            'required': False,
                            'help_text': '',
                            'include_in_list': True,
                            'choices': [],
                            'related_entity': None,
                            'is_calculated': True,
                            'calculation_expression': '25 * 2',
                            'visibility_condition': 'service_type == "Transport"',
                            'validation_expression': 'value >= 0',
                            'validation_message': 'Travel total must stay positive',
                        },
                    ],
                }
            ],
            'screens': [
                {
                    'title': 'Quote editor',
                    'slug': 'quote-editor',
                    'screen_type': 'form',
                    'entity': 'quote',
                    'include_in_navigation': True,
                }
            ],
        }

        preview = build_project_preview(spec, selected_screen_slug='quote-editor')
        travel_field = next(field for field in preview['preview']['fields'] if field['name'] == 'travel_total')

        self.assertFalse(travel_field['sample_visible'])
        self.assertEqual(travel_field['placeholder'], 50)
        self.assertEqual(
            [token['label'] for token in travel_field['rule_tokens']],
            ['Calculated', 'Conditional', 'Validated'],
        )


class BuilderWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='builder', password='builder-pass-123')
        self.client = Client()
        self.client.force_login(self.user)
        self.project = PrototypeProject.objects.create(
            name='Builder Ops',
            created_by=self.user,
            template_kind=ProjectTemplate.BLANK,
        )
        self.entity_a = EntityDefinition.objects.create(project=self.project, name='Client', plural_name='Clients', order=1)
        self.entity_b = EntityDefinition.objects.create(project=self.project, name='Quote', plural_name='Quotes', order=2)
        self.field = FieldDefinition.objects.create(
            entity=self.entity_a,
            name='full_name',
            label='Full name',
            field_type=FieldType.SHORT_TEXT,
            order=1,
        )
        self.state = WorkflowState.objects.create(project=self.project, name='Draft', is_initial=True, order=1)
        self.screen = ScreenDefinition.objects.create(
            project=self.project,
            title='Client List',
            screen_type=ScreenType.LIST,
            entity=self.entity_a,
            order=1,
        )

    def test_entity_update_and_move(self):
        update_response = self.client.post(
            reverse('entity-update', kwargs={'slug': self.project.slug, 'entity_slug': self.entity_a.slug}),
            {'name': 'Participant', 'plural_name': 'Participants', 'description': 'Primary record'},
        )
        self.assertRedirects(update_response, self.project.get_absolute_url())
        self.entity_a.refresh_from_db()
        self.assertEqual(self.entity_a.name, 'Participant')

        move_response = self.client.post(
            reverse('entity-move', kwargs={'slug': self.project.slug, 'entity_slug': self.entity_a.slug, 'direction': 'down'})
        )
        self.assertRedirects(move_response, self.project.get_absolute_url())
        self.entity_a.refresh_from_db()
        self.entity_b.refresh_from_db()
        self.assertGreater(self.entity_a.order, self.entity_b.order)

    def test_field_delete_and_preview_page(self):
        preview_response = self.client.get(reverse('project-preview', kwargs={'slug': self.project.slug}))
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Prototype preview')
        self.assertContains(preview_response, self.screen.title)

        delete_response = self.client.post(
            reverse(
                'field-delete',
                kwargs={'slug': self.project.slug, 'entity_slug': self.entity_a.slug, 'field_id': self.field.pk},
            )
        )
        self.assertRedirects(delete_response, self.entity_a.get_absolute_url())
        self.assertFalse(FieldDefinition.objects.filter(pk=self.field.pk).exists())

    def test_entity_editor_shows_rule_builder_workspace(self):
        response = self.client.get(
            reverse('entity-detail', kwargs={'slug': self.project.slug, 'entity_slug': self.entity_a.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rule builder')
        self.assertContains(response, 'rule-builder-config')
        self.assertContains(response, 'Use formula')

    def test_invalid_field_submission_returns_inline_errors(self):
        response = self.client.post(
            reverse('field-add', kwargs={'slug': self.project.slug, 'entity_slug': self.entity_a.slug}),
            {
                'name': 'derived_total',
                'label': 'Derived total',
                'field_type': FieldType.DECIMAL,
                'include_in_list': 'on',
                'is_calculated': 'on',
                'calculation_expression': 'weekly_hours *',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Rule expression has invalid syntax.', status_code=400)
        self.assertContains(response, 'Rule builder', status_code=400)

    @patch('builder.views.start_project_runtime')
    def test_run_project_starts_runtime(self, mock_start_runtime):
        mock_start_runtime.return_value = {'pid': 99901, 'port': 8751, 'started_at': '2026-03-07T14:30:00+00:00'}

        response = self.client.post(reverse('project-run', kwargs={'slug': self.project.slug}))

        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertEqual(mock_start_runtime.call_args.args[0].pk, self.project.pk)

    @patch('builder.views.stop_project_runtime')
    def test_stop_project_stops_runtime(self, mock_stop_runtime):
        mock_stop_runtime.return_value = True

        response = self.client.post(reverse('project-stop', kwargs={'slug': self.project.slug}))

        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertEqual(mock_stop_runtime.call_args.args[0].pk, self.project.pk)

    @patch('builder.views.get_project_runtime')
    def test_project_detail_shows_runtime_link_when_running(self, mock_get_runtime):
        mock_get_runtime.return_value = {'pid': 99901, 'port': 8751, 'started_at': '2026-03-07T14:30:00+00:00'}

        response = self.client.get(reverse('project-detail', kwargs={'slug': self.project.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open prototype')
        self.assertContains(response, 'http://127.0.0.1:8751')


class AuthorizationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='owner-pass-123')
        self.other = User.objects.create_user(username='other', password='other-pass-123')
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)
        self.other_client = Client()
        self.other_client.force_login(self.other)
        self.project = PrototypeProject.objects.create(
            name='Owner Project',
            created_by=self.owner,
            template_kind=ProjectTemplate.BLANK,
        )

    def test_owner_can_view_project_detail(self):
        response = self.owner_client.get(reverse('project-detail', kwargs={'slug': self.project.slug}))
        self.assertEqual(response.status_code, 200)

    def test_other_user_gets_404_on_project_detail(self):
        response = self.other_client.get(reverse('project-detail', kwargs={'slug': self.project.slug}))
        self.assertEqual(response.status_code, 404)

    def test_other_user_gets_404_on_add_entity(self):
        response = self.other_client.post(
            reverse('entity-add', kwargs={'slug': self.project.slug}),
            {'name': 'Hack', 'plural_name': 'Hacks', 'description': ''},
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_gets_404_on_generate(self):
        response = self.other_client.post(reverse('project-generate', kwargs={'slug': self.project.slug}))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_shows_only_own_projects(self):
        PrototypeProject.objects.create(name='Other Project', created_by=self.other)
        response = self.owner_client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['projects']), 1)
        self.assertEqual(response.context['projects'][0].pk, self.project.pk)

    def test_other_user_gets_404_on_download_artifact(self):
        from .models import GeneratedArtifact
        artifact = GeneratedArtifact.objects.create(
            project=self.project, artifact_type='zip', relative_path='test/archive.zip',
        )
        response = self.other_client.get(reverse('artifact-download', kwargs={'artifact_id': artifact.pk}))
        self.assertEqual(response.status_code, 404)

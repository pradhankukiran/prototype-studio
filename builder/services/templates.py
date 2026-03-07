from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    EntityDefinition,
    FieldDefinition,
    FieldType,
    ProjectTemplate,
    PrototypeProject,
    ScreenDefinition,
    ScreenType,
    WorkflowState,
)


@dataclass(frozen=True)
class TemplateBlueprint:
    entities: list[dict]
    workflow_states: list[dict]
    screens: list[dict]


TEMPLATE_BLUEPRINTS: dict[str, TemplateBlueprint] = {
    ProjectTemplate.QUOTE_BUILDER: TemplateBlueprint(
        entities=[
            {
                'name': 'Client',
                'plural_name': 'Clients',
                'description': 'People receiving support and quotes.',
                'fields': [
                    {'name': 'full_name', 'label': 'Full name', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'support_location', 'label': 'Support location', 'field_type': FieldType.SHORT_TEXT},
                    {'name': 'plan_start', 'label': 'Plan start', 'field_type': FieldType.DATE},
                ],
            },
            {
                'name': 'Quote',
                'plural_name': 'Quotes',
                'description': 'Commercial offer with dates, totals, and approvals.',
                'fields': [
                    {'name': 'quote_number', 'label': 'Quote number', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'client', 'label': 'Client', 'field_type': FieldType.RELATION, 'related_entity': 'client', 'required': True},
                    {'name': 'service_mix', 'label': 'Service mix', 'field_type': FieldType.LONG_TEXT},
                    {'name': 'weekly_hours', 'label': 'Weekly hours', 'field_type': FieldType.DECIMAL},
                    {'name': 'total_value', 'label': 'Total value', 'field_type': FieldType.DECIMAL},
                ],
            },
            {
                'name': 'Line Item',
                'plural_name': 'Line Items',
                'description': 'Granular services inside a quote.',
                'fields': [
                    {'name': 'quote', 'label': 'Quote', 'field_type': FieldType.RELATION, 'related_entity': 'quote', 'required': True},
                    {'name': 'service_type', 'label': 'Service type', 'field_type': FieldType.CHOICE, 'choices_text': 'Personal Assistance\nCommunity Participation\nSupported Independent Living'},
                    {'name': 'hours', 'label': 'Hours', 'field_type': FieldType.DECIMAL},
                    {'name': 'rate', 'label': 'Rate', 'field_type': FieldType.DECIMAL},
                ],
            },
            {
                'name': 'Staff',
                'plural_name': 'Staff',
                'description': 'Approvers and assignees.',
                'fields': [
                    {'name': 'full_name', 'label': 'Full name', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'role', 'label': 'Role', 'field_type': FieldType.CHOICE, 'choices_text': 'Service Manager\nService Lead\nFinance'},
                    {'name': 'email', 'label': 'Email', 'field_type': FieldType.SHORT_TEXT},
                ],
            },
        ],
        workflow_states=[
            {'name': 'Draft', 'is_initial': True},
            {'name': 'Reviewed'},
            {'name': 'Approved', 'is_terminal': True},
        ],
        screens=[
            {'title': 'Delivery Snapshot', 'screen_type': ScreenType.DASHBOARD},
            {'title': 'Quotes', 'screen_type': ScreenType.LIST, 'entity': 'quote'},
            {'title': 'Quote Editor', 'screen_type': ScreenType.FORM, 'entity': 'quote'},
            {'title': 'Quote Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'quote'},
            {'title': 'Clients', 'screen_type': ScreenType.LIST, 'entity': 'client'},
            {'title': 'Client Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'client'},
            {'title': 'Line Items', 'screen_type': ScreenType.LIST, 'entity': 'line-item'},
        ],
    ),
    ProjectTemplate.CRM: TemplateBlueprint(
        entities=[
            {
                'name': 'Organisation',
                'plural_name': 'Organisations',
                'description': 'Referral sources and customer accounts.',
                'fields': [
                    {'name': 'name', 'label': 'Name', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'segment', 'label': 'Segment', 'field_type': FieldType.CHOICE, 'choices_text': 'Referrer\nPartner\nCustomer'},
                    {'name': 'website', 'label': 'Website', 'field_type': FieldType.SHORT_TEXT},
                ],
            },
            {
                'name': 'Contact',
                'plural_name': 'Contacts',
                'description': 'Key people linked to organisations.',
                'fields': [
                    {'name': 'full_name', 'label': 'Full name', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'organisation', 'label': 'Organisation', 'field_type': FieldType.RELATION, 'related_entity': 'organisation'},
                    {'name': 'email', 'label': 'Email', 'field_type': FieldType.SHORT_TEXT},
                    {'name': 'phone', 'label': 'Phone', 'field_type': FieldType.SHORT_TEXT},
                ],
            },
            {
                'name': 'Opportunity',
                'plural_name': 'Opportunities',
                'description': 'Pipeline record for new business.',
                'fields': [
                    {'name': 'title', 'label': 'Title', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'contact', 'label': 'Contact', 'field_type': FieldType.RELATION, 'related_entity': 'contact'},
                    {'name': 'estimated_value', 'label': 'Estimated value', 'field_type': FieldType.DECIMAL},
                    {'name': 'next_step', 'label': 'Next step', 'field_type': FieldType.LONG_TEXT},
                ],
            },
        ],
        workflow_states=[
            {'name': 'New', 'is_initial': True},
            {'name': 'Qualified'},
            {'name': 'Won', 'is_terminal': True},
            {'name': 'Lost', 'is_terminal': True},
        ],
        screens=[
            {'title': 'Pipeline Pulse', 'screen_type': ScreenType.DASHBOARD},
            {'title': 'Opportunities', 'screen_type': ScreenType.LIST, 'entity': 'opportunity'},
            {'title': 'Opportunity Editor', 'screen_type': ScreenType.FORM, 'entity': 'opportunity'},
            {'title': 'Opportunity Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'opportunity'},
            {'title': 'Contacts', 'screen_type': ScreenType.LIST, 'entity': 'contact'},
            {'title': 'Contact Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'contact'},
        ],
    ),
    ProjectTemplate.APPROVAL_FLOW: TemplateBlueprint(
        entities=[
            {
                'name': 'Request',
                'plural_name': 'Requests',
                'description': 'Change or procurement request awaiting sign-off.',
                'fields': [
                    {'name': 'title', 'label': 'Title', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'owner', 'label': 'Owner', 'field_type': FieldType.SHORT_TEXT},
                    {'name': 'budget_impact', 'label': 'Budget impact', 'field_type': FieldType.DECIMAL},
                    {'name': 'justification', 'label': 'Justification', 'field_type': FieldType.LONG_TEXT},
                ],
            },
            {
                'name': 'Approval',
                'plural_name': 'Approvals',
                'description': 'Approver feedback and decision.',
                'fields': [
                    {'name': 'request', 'label': 'Request', 'field_type': FieldType.RELATION, 'related_entity': 'request', 'required': True},
                    {'name': 'approver_name', 'label': 'Approver name', 'field_type': FieldType.SHORT_TEXT},
                    {'name': 'decision', 'label': 'Decision', 'field_type': FieldType.CHOICE, 'choices_text': 'Approve\nReject\nNeeds Changes'},
                    {'name': 'commentary', 'label': 'Commentary', 'field_type': FieldType.LONG_TEXT},
                ],
            },
        ],
        workflow_states=[
            {'name': 'Submitted', 'is_initial': True},
            {'name': 'In Review'},
            {'name': 'Approved', 'is_terminal': True},
            {'name': 'Rejected', 'is_terminal': True},
        ],
        screens=[
            {'title': 'Approvals Board', 'screen_type': ScreenType.DASHBOARD},
            {'title': 'Requests', 'screen_type': ScreenType.LIST, 'entity': 'request'},
            {'title': 'Request Form', 'screen_type': ScreenType.FORM, 'entity': 'request'},
            {'title': 'Request Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'request'},
            {'title': 'Approvals', 'screen_type': ScreenType.LIST, 'entity': 'approval'},
            {'title': 'Approval Form', 'screen_type': ScreenType.FORM, 'entity': 'approval'},
        ],
    ),
    ProjectTemplate.CASE_TRACKER: TemplateBlueprint(
        entities=[
            {
                'name': 'Case',
                'plural_name': 'Cases',
                'description': 'Issue or service case owned by a team.',
                'fields': [
                    {'name': 'title', 'label': 'Title', 'field_type': FieldType.SHORT_TEXT, 'required': True},
                    {'name': 'category', 'label': 'Category', 'field_type': FieldType.CHOICE, 'choices_text': 'Incident\nComplaint\nReview'},
                    {'name': 'opened_on', 'label': 'Opened on', 'field_type': FieldType.DATE},
                    {'name': 'summary', 'label': 'Summary', 'field_type': FieldType.LONG_TEXT},
                ],
            },
            {
                'name': 'Activity',
                'plural_name': 'Activities',
                'description': 'Timeline entries within a case.',
                'fields': [
                    {'name': 'case', 'label': 'Case', 'field_type': FieldType.RELATION, 'related_entity': 'case', 'required': True},
                    {'name': 'entry_date', 'label': 'Entry date', 'field_type': FieldType.DATE},
                    {'name': 'notes', 'label': 'Notes', 'field_type': FieldType.LONG_TEXT},
                ],
            },
        ],
        workflow_states=[
            {'name': 'Open', 'is_initial': True},
            {'name': 'Investigating'},
            {'name': 'Closed', 'is_terminal': True},
        ],
        screens=[
            {'title': 'Case Command', 'screen_type': ScreenType.DASHBOARD},
            {'title': 'Cases', 'screen_type': ScreenType.LIST, 'entity': 'case'},
            {'title': 'Case Form', 'screen_type': ScreenType.FORM, 'entity': 'case'},
            {'title': 'Case Detail', 'screen_type': ScreenType.DETAIL, 'entity': 'case'},
            {'title': 'Activities', 'screen_type': ScreenType.LIST, 'entity': 'activity'},
        ],
    ),
}


def seed_project_from_template(project: PrototypeProject) -> None:
    if project.template_kind == ProjectTemplate.BLANK or project.entities.exists():
        return

    blueprint = TEMPLATE_BLUEPRINTS.get(project.template_kind)
    if not blueprint:
        return

    entities_by_slug: dict[str, EntityDefinition] = {}
    pending_fields: list[tuple[EntityDefinition, dict]] = []

    for index, entity_blueprint in enumerate(blueprint.entities, start=1):
        entity = EntityDefinition.objects.create(
            project=project,
            name=entity_blueprint['name'],
            plural_name=entity_blueprint.get('plural_name', ''),
            description=entity_blueprint.get('description', ''),
            order=index,
        )
        entities_by_slug[entity.slug] = entity
        for field_blueprint in entity_blueprint.get('fields', []):
            pending_fields.append((entity, field_blueprint))

    for index, (entity, field_blueprint) in enumerate(pending_fields, start=1):
        related_slug = field_blueprint.get('related_entity')
        FieldDefinition.objects.create(
            entity=entity,
            name=field_blueprint['name'],
            label=field_blueprint.get('label', ''),
            field_type=field_blueprint['field_type'],
            required=field_blueprint.get('required', False),
            help_text=field_blueprint.get('help_text', ''),
            include_in_list=field_blueprint.get('include_in_list', True),
            choices_text=field_blueprint.get('choices_text', ''),
            related_entity=entities_by_slug.get(related_slug) if related_slug else None,
            order=index,
        )

    for index, state_blueprint in enumerate(blueprint.workflow_states, start=1):
        WorkflowState.objects.create(
            project=project,
            name=state_blueprint['name'],
            is_initial=state_blueprint.get('is_initial', False),
            is_terminal=state_blueprint.get('is_terminal', False),
            order=index,
        )

    for index, screen_blueprint in enumerate(blueprint.screens, start=1):
        ScreenDefinition.objects.create(
            project=project,
            title=screen_blueprint['title'],
            screen_type=screen_blueprint['screen_type'],
            entity=entities_by_slug.get(screen_blueprint.get('entity')) if screen_blueprint.get('entity') else None,
            include_in_navigation=screen_blueprint.get('include_in_navigation', True),
            order=index,
        )

from __future__ import annotations

from itertools import cycle

from .rules import RuleExpressionError, evaluate_rule_expression


def _title_from_slug(slug: str | None) -> str:
    if not slug:
        return 'Record'
    return slug.replace('-', ' ').replace('_', ' ').title()


def _sample_value(field: dict, index: int = 1) -> str | int | float | bool:
    field_type = field['field_type']
    label = field['label']
    if field_type == 'short_text':
        return f'{label} {index}'
    if field_type == 'long_text':
        return f'Sample {label.lower()} for review and prototype validation.'
    if field_type == 'integer':
        return index * 2
    if field_type == 'decimal':
        return float(index * 125)
    if field_type == 'date':
        return f'2026-03-0{index}'
    if field_type == 'boolean':
        return index % 2 == 0
    if field_type == 'choice':
        return field['choices'][0] if field.get('choices') else 'Option'
    if field_type == 'relation':
        return f'{_title_from_slug(field.get("related_entity"))} #{index}'
    return f'{label} {index}'


def _build_sample_context(entity: dict, index: int = 1) -> dict:
    context: dict[str, str | int | float | bool] = {}
    for field in entity['fields']:
        if field.get('is_calculated') and field.get('calculation_expression'):
            try:
                context[field['name']] = evaluate_rule_expression(
                    field['calculation_expression'],
                    context,
                )
            except (RuleExpressionError, TypeError, ValueError, ZeroDivisionError):
                context[field['name']] = 'Rule preview unavailable'
            continue
        context[field['name']] = _sample_value(field, index)
    return context


def _field_rule_tokens(field: dict) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    if field['required']:
        tokens.append({'label': 'Required', 'tone': 'positive'})
    if field.get('is_calculated'):
        tokens.append({'label': 'Calculated', 'tone': 'positive'})
    if field.get('visibility_condition'):
        tokens.append({'label': 'Conditional', 'tone': 'warn'})
    if field.get('validation_expression'):
        tokens.append({'label': 'Validated', 'tone': 'warn'})
    if field.get('related_entity'):
        tokens.append({'label': _title_from_slug(field['related_entity']), 'tone': 'default'})
    return tokens


def _field_visible_in_sample(field: dict, context: dict) -> bool:
    expression = (field.get('visibility_condition') or '').strip()
    if not expression:
        return True
    try:
        return bool(evaluate_rule_expression(expression, context))
    except (RuleExpressionError, TypeError, ValueError, ZeroDivisionError):
        return True


def _build_dashboard_preview(spec: dict) -> dict:
    entity_cards = [
        {
            'title': entity['plural_name'],
            'value': len(entity['fields']) * 3 or 1,
            'meta': entity['description'] or 'No description provided.',
        }
        for entity in spec['entities']
    ]
    return {
        'mode': 'dashboard',
        'entity_cards': entity_cards,
        'workflow_states': spec['workflow_states'],
    }


def _build_list_preview(spec: dict, screen: dict) -> dict:
    entity = next(entity for entity in spec['entities'] if entity['slug'] == screen['entity'])
    columns = ['ID']
    if spec['workflow_states']:
        columns.append('State')
    list_fields = [field for field in entity['fields'] if field['include_in_list']]
    if not list_fields:
        list_fields = entity['fields'][:4]
    columns.extend(field['label'] for field in list_fields)
    state_names = [state['name'] for state in spec['workflow_states']] or ['Draft']
    rows = []
    for index, state_name in zip(range(1, 4), cycle(state_names), strict=False):
        sample_context = _build_sample_context(entity, index)
        row = {'ID': index}
        if spec['workflow_states']:
            row['State'] = state_name
        for field in list_fields:
            row[field['label']] = sample_context.get(field['name'], _sample_value(field, index))
        rows.append(row)
    return {
        'mode': 'list',
        'entity': entity,
        'columns': columns,
        'rows': rows,
    }


def _build_form_preview(spec: dict, screen: dict) -> dict:
    entity = next(entity for entity in spec['entities'] if entity['slug'] == screen['entity'])
    sample_context = _build_sample_context(entity)
    return {
        'mode': 'form',
        'entity': entity,
        'workflow_states': spec['workflow_states'],
        'fields': [
            {
                'name': field['name'],
                'label': field['label'],
                'type_label': field['field_type'].replace('_', ' ').title(),
                'help_text': field['help_text'],
                'placeholder': sample_context.get(field['name'], _sample_value(field)),
                'rule_tokens': _field_rule_tokens(field),
                'sample_visible': _field_visible_in_sample(field, sample_context),
                'calculation_expression': field.get('calculation_expression', ''),
                'visibility_condition': field.get('visibility_condition', ''),
                'validation_expression': field.get('validation_expression', ''),
            }
            for field in entity['fields']
        ],
    }


def _build_detail_preview(spec: dict, screen: dict) -> dict:
    entity = next(entity for entity in spec['entities'] if entity['slug'] == screen['entity'])
    sample_context = _build_sample_context(entity)
    return {
        'mode': 'detail',
        'entity': entity,
        'workflow_state': spec['workflow_states'][0]['name'] if spec['workflow_states'] else None,
        'fields': [
            {
                'label': field['label'],
                'value': sample_context.get(field['name'], _sample_value(field)),
                'rule_tokens': _field_rule_tokens(field),
            }
            for field in entity['fields']
        ],
    }


def build_project_preview(spec: dict, selected_screen_slug: str | None = None) -> dict:
    screens = spec['screens']
    selected_screen = None
    if screens:
        selected_screen = next(
            (screen for screen in screens if screen['slug'] == selected_screen_slug),
            screens[0],
        )

    if not selected_screen:
        preview = {
            'mode': 'empty',
            'entity_cards': [
                {
                    'title': entity['plural_name'],
                    'value': len(entity['fields']),
                    'meta': entity['description'] or 'No description provided.',
                }
                for entity in spec['entities']
            ],
        }
    elif selected_screen['screen_type'] == 'dashboard':
        preview = _build_dashboard_preview(spec)
    elif selected_screen['screen_type'] == 'list':
        preview = _build_list_preview(spec, selected_screen)
    elif selected_screen['screen_type'] == 'form':
        preview = _build_form_preview(spec, selected_screen)
    else:
        preview = _build_detail_preview(spec, selected_screen)

    return {
        'screens': screens,
        'selected_screen': selected_screen,
        'preview': preview,
    }

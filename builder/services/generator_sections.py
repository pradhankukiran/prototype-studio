from __future__ import annotations

import json
import textwrap

from .generator_css import build_css

# Triple-quote marker used in generated code
TQ = "'''"


def section_imports() -> str:
    return textwrap.dedent("""\
        from __future__ import annotations

        import ast
        import csv
        import io
        import json
        import operator
        import sqlite3
        from datetime import date, timedelta
        from pathlib import Path

        import streamlit as st""")


def section_constants(spec: dict, theme: dict, profile: dict) -> str:
    spec_json = json.dumps(spec, indent=2)
    theme_json = json.dumps(theme, indent=2)
    profile_json = json.dumps(profile, indent=2)
    return textwrap.dedent(f"""\
        APP_DIR = Path(__file__).resolve().parent
        DB_PATH = APP_DIR / "prototype.db"
        SPEC = json.loads({repr(spec_json)})
        THEME = json.loads({repr(theme_json)})
        PROFILE = json.loads({repr(profile_json)})""")


def section_database() -> str:
    return textwrap.dedent("""\
        def get_connection() -> sqlite3.Connection:
            connection = sqlite3.connect(DB_PATH)
            connection.row_factory = sqlite3.Row
            return connection


        def sql_type(field: dict) -> str:
            mapping = {
                "short_text": "TEXT",
                "long_text": "TEXT",
                "integer": "INTEGER",
                "decimal": "REAL",
                "date": "TEXT",
                "boolean": "INTEGER",
                "choice": "TEXT",
                "relation": "INTEGER",
            }
            return mapping[field["field_type"]]


        def workflow_enabled() -> bool:
            return bool(SPEC["workflow_states"])


        def default_state() -> str:
            for state in SPEC["workflow_states"]:
                if state["is_initial"]:
                    return state["name"]
            return SPEC["workflow_states"][0]["name"] if SPEC["workflow_states"] else ""


        def ensure_database() -> None:
            with get_connection() as connection:
                for entity in SPEC["entities"]:
                    columns = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
                    if workflow_enabled():
                        columns.append('workflow_state TEXT')
                    for field in entity["fields"]:
                        columns.append(f'"{field["name"]}" {sql_type(field)}')
                    connection.execute(
                        f'CREATE TABLE IF NOT EXISTS "{entity["slug"]}" ({", ".join(columns)})'
                    )
                connection.commit()""")


def section_rule_engine() -> str:
    return textwrap.dedent("""\
        class RuleExpressionError(ValueError):
            pass


        ALLOWED_FUNCTIONS = {
            "abs": abs,
            "float": float,
            "int": int,
            "len": len,
            "max": max,
            "min": min,
            "round": round,
            "str": str,
        }

        ALLOWED_BINARY_OPERATORS = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
        }

        ALLOWED_UNARY_OPERATORS = {
            ast.Not: operator.not_,
            ast.UAdd: operator.pos,
            ast.USub: operator.neg,
        }

        ALLOWED_COMPARE_OPERATORS = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
        }


        def validate_rule_expression(expression: str) -> None:
            expression = (expression or "").strip()
            if not expression:
                return
            try:
                parsed = ast.parse(expression, mode="eval")
            except SyntaxError as exc:
                raise RuleExpressionError("Rule expression has invalid syntax.") from exc
            _validate_node(parsed.body)


        def evaluate_rule_expression(expression: str, context: dict[str, object]) -> object:
            validate_rule_expression(expression)
            parsed = ast.parse(expression, mode="eval")
            return _evaluate_node(parsed.body, context)


        def _validate_node(node: ast.AST) -> None:
            if isinstance(node, (ast.Constant, ast.Name)):
                return
            if isinstance(node, ast.BinOp):
                if type(node.op) not in ALLOWED_BINARY_OPERATORS:
                    raise RuleExpressionError("Unsupported operator in rule expression.")
                _validate_node(node.left)
                _validate_node(node.right)
                return
            if isinstance(node, ast.UnaryOp):
                if type(node.op) not in ALLOWED_UNARY_OPERATORS:
                    raise RuleExpressionError("Unsupported unary operator in rule expression.")
                _validate_node(node.operand)
                return
            if isinstance(node, ast.BoolOp):
                for value in node.values:
                    _validate_node(value)
                return
            if isinstance(node, ast.Compare):
                _validate_node(node.left)
                for comparator in node.comparators:
                    _validate_node(comparator)
                for operator_node in node.ops:
                    if type(operator_node) not in ALLOWED_COMPARE_OPERATORS:
                        raise RuleExpressionError("Unsupported comparison in rule expression.")
                return
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                    raise RuleExpressionError("Only basic helper functions are allowed in rule expressions.")
                for argument in node.args:
                    _validate_node(argument)
                for keyword in node.keywords:
                    _validate_node(keyword.value)
                return
            if isinstance(node, ast.IfExp):
                _validate_node(node.test)
                _validate_node(node.body)
                _validate_node(node.orelse)
                return
            raise RuleExpressionError("Unsupported construct in rule expression.")


        def _evaluate_node(node: ast.AST, context: dict[str, object]) -> object:
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                if node.id not in context:
                    raise RuleExpressionError(f"Unknown field reference: {node.id}")
                return context[node.id]
            if isinstance(node, ast.BinOp):
                left = _evaluate_node(node.left, context)
                right = _evaluate_node(node.right, context)
                return ALLOWED_BINARY_OPERATORS[type(node.op)](left, right)
            if isinstance(node, ast.UnaryOp):
                operand = _evaluate_node(node.operand, context)
                return ALLOWED_UNARY_OPERATORS[type(node.op)](operand)
            if isinstance(node, ast.BoolOp):
                values = [_evaluate_node(value, context) for value in node.values]
                if isinstance(node.op, ast.And):
                    return all(values)
                return any(values)
            if isinstance(node, ast.Compare):
                left = _evaluate_node(node.left, context)
                for operator_node, comparator in zip(node.ops, node.comparators, strict=False):
                    right = _evaluate_node(comparator, context)
                    if not ALLOWED_COMPARE_OPERATORS[type(operator_node)](left, right):
                        return False
                    left = right
                return True
            if isinstance(node, ast.Call):
                function = ALLOWED_FUNCTIONS[node.func.id]
                arguments = [_evaluate_node(argument, context) for argument in node.args]
                keyword_arguments = {
                    keyword.arg: _evaluate_node(keyword.value, context)
                    for keyword in node.keywords
                }
                return function(*arguments, **keyword_arguments)
            if isinstance(node, ast.IfExp):
                return _evaluate_node(node.body, context) if _evaluate_node(node.test, context) else _evaluate_node(node.orelse, context)
            raise RuleExpressionError("Unsupported construct in rule expression.")


        def safe_rule_value(expression: str, context: dict[str, object], default=None):
            expression = (expression or "").strip()
            if not expression:
                return default
            try:
                return evaluate_rule_expression(expression, context)
            except (RuleExpressionError, TypeError, ValueError, ZeroDivisionError):
                return default""")


def _md(html_template: str) -> str:
    """Generate a st.markdown() call with unsafe_allow_html for an f-string HTML template.

    The html_template uses single braces for f-string interpolation in the generated code.
    """
    return (
        "st.markdown(\n"
        f"        f{TQ}\n"
        f"        {html_template}\n"
        f"        {TQ},\n"
        "        unsafe_allow_html=True,\n"
        "    )"
    )


def _md_indent(html_template: str, indent: int = 8) -> str:
    """Like _md but with configurable indentation."""
    pad = " " * indent
    return (
        f"{pad}st.markdown(\n"
        f"{pad}    f{TQ}\n"
        f"{pad}    {html_template}\n"
        f"{pad}    {TQ},\n"
        f"{pad}    unsafe_allow_html=True,\n"
        f"{pad})"
    )


def section_helpers() -> str:
    # Build helper functions. For functions that contain triple-quoted f-strings
    # (st.markdown with HTML), we construct those lines carefully.

    return (
        textwrap.dedent("""\
        def get_entity(entity_slug: str) -> dict:
            return next(entity for entity in SPEC["entities"] if entity["slug"] == entity_slug)


        def first_text_field(entity: dict) -> str | None:
            for field in entity["fields"]:
                if field["field_type"] in {"short_text", "choice"}:
                    return field["name"]
            return entity["fields"][0]["name"] if entity["fields"] else None


        def fetch_records(entity: dict) -> list[sqlite3.Row]:
            order_column = "id DESC"
            for field in entity["fields"]:
                if field.get("include_in_list"):
                    order_column = f'"{field["name"]}" COLLATE NOCASE ASC, id DESC'
                    break
            with get_connection() as connection:
                return list(connection.execute(f'SELECT * FROM "{entity["slug"]}" ORDER BY {order_column}'))


        def relation_options(field: dict) -> tuple[list[int | None], dict[int, str]]:
            if not field.get("related_entity"):
                return [None], {}
            related_entity = get_entity(field["related_entity"])
            label_field = first_text_field(related_entity)
            records = fetch_records(related_entity)
            label_map = {
                row["id"]: (
                    str(row[label_field])
                    if label_field and row[label_field] not in (None, "")
                    else f'{related_entity["name"]} #{row["id"]}'
                )
                for row in records
            }
            return [None] + list(label_map.keys()), label_map


        def normalize_stored_value(field: dict, value):
            if value is None:
                return None
            if field["field_type"] == "boolean":
                return bool(value)
            return value


        def default_input_value(field: dict):
            field_type = field["field_type"]
            if field_type in {"short_text", "long_text"}:
                return ""
            if field_type == "integer":
                return 0
            if field_type == "decimal":
                return 0.0
            if field_type == "date":
                return date.today().isoformat()
            if field_type == "boolean":
                return False
            if field_type == "choice":
                return ""
            return None


        def widget_key(key_prefix: str, field_name: str) -> str:
            return f"{key_prefix}_{field_name}"


        def format_field_value(field: dict, value) -> str:
            if value in (None, ""):
                return ""
            if field["field_type"] == "boolean":
                return "Yes" if value else "No"
            return str(value)


        def serialize_record(entity: dict, row: sqlite3.Row) -> dict:
            payload = {"ID": row["id"]}
            if workflow_enabled():
                payload["State"] = row["workflow_state"]
            for field in entity["fields"]:
                value = row[field["name"]]
                if field["field_type"] == "boolean":
                    value = bool(value)
                elif field["field_type"] == "relation" and value:
                    _, label_map = relation_options(field)
                    value = label_map.get(value, f'Record #{value}')
                payload[field["label"]] = value
            return payload


        def insert_record(entity: dict, values: dict) -> None:
            columns = []
            placeholders = []
            params = []
            if workflow_enabled():
                columns.append("workflow_state")
                placeholders.append("?")
                params.append(values.get("workflow_state", default_state()))
            for field in entity["fields"]:
                columns.append(f'"{field["name"]}"')
                placeholders.append("?")
                params.append(values.get(field["name"]))
            with get_connection() as connection:
                connection.execute(
                    f'INSERT INTO "{entity["slug"]}" ({", ".join(columns)}) VALUES ({", ".join(placeholders)})',
                    params,
                )
                connection.commit()


        def update_record(entity: dict, record_id: int, values: dict) -> None:
            assignments = []
            params = []
            if workflow_enabled():
                assignments.append("workflow_state = ?")
                params.append(values.get("workflow_state", default_state()))
            for field in entity["fields"]:
                assignments.append(f'"{field["name"]}" = ?')
                params.append(values.get(field["name"]))
            params.append(record_id)
            with get_connection() as connection:
                connection.execute(
                    f'UPDATE "{entity["slug"]}" SET {", ".join(assignments)} WHERE id = ?',
                    params,
                )
                connection.commit()


        def collect_current_values(entity: dict, selected_row: sqlite3.Row | None, key_prefix: str) -> dict:
            values = {}
            for field in entity["fields"]:
                state_key = widget_key(key_prefix, field["name"])
                if state_key in st.session_state:
                    value = st.session_state[state_key]
                    if field["field_type"] == "date" and value:
                        value = value.isoformat()
                    values[field["name"]] = value
                    continue
                stored_value = normalize_stored_value(
                    field,
                    selected_row[field["name"]] if selected_row else None,
                )
                values[field["name"]] = (
                    stored_value if stored_value is not None else default_input_value(field)
                )
            return values


        def hydrate_calculated_fields(entity: dict, values: dict) -> dict:
            resolved = dict(values)
            for field in entity["fields"]:
                if field.get("is_calculated") and field.get("calculation_expression"):
                    resolved[field["name"]] = safe_rule_value(
                        field["calculation_expression"],
                        resolved,
                        resolved.get(field["name"]),
                    )
            return resolved


        def field_is_visible(field: dict, values: dict) -> bool:
            condition = (field.get("visibility_condition") or "").strip()
            if not condition:
                return True
            return bool(safe_rule_value(condition, values, True))


        def clear_form_state(entity: dict, key_prefix: str) -> None:
            keys = [widget_key(key_prefix, field["name"]) for field in entity["fields"]]
            if workflow_enabled():
                keys.append(widget_key(key_prefix, "workflow_state"))
            for state_key in keys:
                st.session_state.pop(state_key, None)


        def render_field_input(field: dict, current_value, key_prefix: str):
            key = widget_key(key_prefix, field["name"])
            help_text = field.get("help_text") or None
            field_type = field["field_type"]

            if field_type == "short_text":
                return st.text_input(field["label"], value=current_value or "", help=help_text, key=key)
            if field_type == "long_text":
                return st.text_area(field["label"], value=current_value or "", help=help_text, key=key)
            if field_type == "integer":
                return st.number_input(field["label"], value=int(current_value or 0), step=1, help=help_text, key=key)
            if field_type == "decimal":
                return st.number_input(field["label"], value=float(current_value or 0.0), step=0.5, help=help_text, key=key)
            if field_type == "date":
                raw_value = current_value or default_input_value(field)
                current_date = date.fromisoformat(raw_value) if isinstance(raw_value, str) else raw_value
                return st.date_input(field["label"], value=current_date, help=help_text, key=key).isoformat()
            if field_type == "boolean":
                return st.checkbox(field["label"], value=bool(current_value), help=help_text, key=key)
            if field_type == "choice":
                options = [""] + (field.get("choices") or [])
                selected = current_value if current_value in options else ""
                return st.selectbox(
                    field["label"],
                    options=options,
                    index=options.index(selected),
                    format_func=lambda value: "Select an option" if value == "" else value,
                    help=help_text,
                    key=key,
                )
            if field_type == "relation":
                options, label_map = relation_options(field)
                current_option = current_value if current_value in label_map else None
                selected = st.selectbox(
                    field["label"],
                    options=options,
                    index=options.index(current_option),
                    format_func=lambda value: "Select a record" if value is None else label_map.get(value, str(value)),
                    help=help_text,
                    key=key,
                )
                return selected
            return st.text_input(field["label"], value=current_value or "", help=help_text, key=key)


        def list_fields_for_entity(entity: dict) -> list[dict]:
            fields = [field for field in entity["fields"] if field.get("include_in_list")]
            return fields or entity["fields"][:4]


        def format_display_value(value) -> str:
            if value in (None, ""):
                return "Not set"
            if isinstance(value, bool):
                return "Yes" if value else "No"
            return str(value)


        def format_record_title(entity: dict, row: sqlite3.Row) -> str:
            label_field = first_text_field(entity)
            if label_field and row[label_field] not in (None, ""):
                return str(row[label_field])
            return f'{entity["name"]} #{row["id"]}'


        """)  # noqa: W291 — trailing space is intentional for the join
        + "def render_screen_header(title: str, description: str, eyebrow: str, badges: list[str] | None = None) -> None:\n"
        "    badge_html = \"\".join(\n"
        "        f'<span class=\"hero-badge\">{badge}</span>' for badge in (badges or [])\n"
        "    )\n"
        "    st.markdown(\n"
        f"        f{TQ}\n"
        '        <section class="hero-header">\n'
        '            <div class="hero-copy">\n'
        '                <p class="hero-eyebrow">{eyebrow}</p>\n'
        '                <h1>{title}</h1>\n'
        '                <p>{description}</p>\n'
        '            </div>\n'
        '            <div class="hero-badge-row">{badge_html}</div>\n'
        '        </section>\n'
        f"        {TQ},\n"
        "        unsafe_allow_html=True,\n"
        "    )\n"
        "\n\n"
        "def render_workflow_strip() -> None:\n"
        '    if not SPEC["workflow_states"]:\n'
        "        return\n"
        "    state_html = \"\".join(\n"
        "        f'<span class=\"workflow-pill{\"\" if not state[\"is_terminal\"] else \" workflow-pill-terminal\"}{\"\" if not state[\"is_initial\"] else \" workflow-pill-start\"}\">{state[\"name\"]}</span>'\n"
        '        for state in SPEC["workflow_states"]\n'
        "    )\n"
        '    st.markdown(f\'<div class="workflow-strip">{state_html}</div>\', unsafe_allow_html=True)\n'
        "\n\n"
        "def render_empty_state(title: str, description: str) -> None:\n"
        "    st.markdown(\n"
        f"        f{TQ}\n"
        '        <div class="empty-state-card">\n'
        '            <h3>{title}</h3>\n'
        '            <p>{description}</p>\n'
        '        </div>\n'
        f"        {TQ},\n"
        "        unsafe_allow_html=True,\n"
        "    )\n"
        "\n\n"
        + textwrap.dedent("""\
        def row_matches_query(entity: dict, row: sqlite3.Row, query: str) -> bool:
            if not query.strip():
                return True
            payload = serialize_record(entity, row)
            haystack = " ".join(
                str(value).lower()
                for value in payload.values()
                if value not in (None, "")
            )
            return query.strip().lower() in haystack


        """)
        + "def render_record_glance_cards(entity: dict, records: list[sqlite3.Row]) -> None:\n"
        "    preview_rows = records[:3]\n"
        "    if not preview_rows:\n"
        "        return\n"
        "    columns = st.columns(len(preview_rows))\n"
        "    display_fields = list_fields_for_entity(entity)[:2]\n"
        "    for column, row in zip(columns, preview_rows, strict=False):\n"
        "        payload = serialize_record(entity, row)\n"
        "        list_html = \"\".join(\n"
        "            f'<li><span>{field[\"label\"]}</span><strong>{format_display_value(payload.get(field[\"label\"]))}</strong></li>'\n"
        "            for field in display_fields\n"
        "        )\n"
        "        state_badge = \"\"\n"
        '        if "State" in payload:\n'
        "            state_badge = f'<span class=\"hero-badge\">{payload[\"State\"]}</span>'\n"
        "        with column:\n"
        "            st.markdown(\n"
        f"                f{TQ}\n"
        '                <div class="glance-card">\n'
        '                    <div class="glance-head">\n'
        "                        <p>{entity[\"name\"]} #{row[\"id\"]}</p>\n"
        "                        {state_badge}\n"
        "                    </div>\n"
        "                    <h3>{format_record_title(entity, row)}</h3>\n"
        '                    <ul class="glance-list">{list_html}</ul>\n'
        "                </div>\n"
        f"                {TQ},\n"
        "                unsafe_allow_html=True,\n"
        "            )\n"
        "\n\n"
        + textwrap.dedent("""\
        def build_column_config(entity: dict) -> dict:
            config = {}
            for field in entity["fields"]:
                ft = field["field_type"]
                label = field["label"]
                if ft == "integer":
                    config[label] = st.column_config.NumberColumn(label, format="%d")
                elif ft == "decimal":
                    config[label] = st.column_config.NumberColumn(label, format="%.2f")
                elif ft == "date":
                    config[label] = st.column_config.DateColumn(label)
                elif ft == "boolean":
                    config[label] = st.column_config.CheckboxColumn(label)
                elif ft == "choice":
                    config[label] = st.column_config.SelectboxColumn(label, options=field.get("choices") or [])
                else:
                    config[label] = st.column_config.TextColumn(label)
            return config


        def records_to_csv(entity: dict, records: list[sqlite3.Row]) -> str:
            rows = [serialize_record(entity, row) for row in records]
            if not rows:
                return ""
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue()


        def find_related_entities(entity_slug: str) -> list[dict]:
            related = []
            for entity in SPEC["entities"]:
                for field in entity["fields"]:
                    if field["field_type"] == "relation" and field.get("related_entity") == entity_slug:
                        related.append({"entity": entity, "field": field})
            return related


        def first_decimal_field(entity: dict) -> str | None:
            for field in entity["fields"]:
                if field["field_type"] == "decimal":
                    return field["name"]
            return None


        def first_date_field(entity: dict) -> str | None:
            for field in entity["fields"]:
                if field["field_type"] == "date":
                    return field["name"]
            return None


        def notify_success(message: str) -> None:
            if PROFILE.get("use_toasts"):
                st.toast(message, icon="\\u2705")
            else:
                st.success(message)""")
    )


def section_navigation(spec: dict, profile: dict) -> str:
    nav_style = profile.get('nav_style', 'sidebar_radio')

    sidebar_brand = (
        "def _render_sidebar_brand() -> None:\n"
        '    total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])\n'
        "    st.sidebar.markdown(\n"
        f"        f{TQ}\n"
        '        <div class="studio-brand">\n'
        '            <span>{THEME["label"]}</span>\n'
        '            <h2>{SPEC["name"]}</h2>\n'
        '            <p>{SPEC["description"] or "Generated from the Prototype Studio schema builder."}</p>\n'
        "        </div>\n"
        f"        {TQ},\n"
        "        unsafe_allow_html=True,\n"
        "    )\n"
        "    sidebar_metrics = st.sidebar.columns(2)\n"
        "    with sidebar_metrics[0]:\n"
        '        st.metric("Entities", len(SPEC["entities"]))\n'
        "    with sidebar_metrics[1]:\n"
        '        st.metric("Records", total_records)\n'
        "    if workflow_enabled():\n"
        "        st.sidebar.markdown('<p class=\"sidebar-label\">Workflow</p>', unsafe_allow_html=True)\n"
        '        st.sidebar.caption(" -> ".join(state["name"] for state in SPEC["workflow_states"]))\n'
    )

    if nav_style == 'sidebar_radio':
        return sidebar_brand + textwrap.dedent("""
        def render_navigation(available_screens: list[dict]) -> dict:
            _render_sidebar_brand()
            labels = [screen["title"] for screen in available_screens]
            selected_label = st.sidebar.radio("Navigation", labels, label_visibility="collapsed")
            return next(screen for screen in available_screens if screen["title"] == selected_label)""")

    if nav_style == 'sidebar_pills':
        return sidebar_brand + textwrap.dedent("""
        def render_navigation(available_screens: list[dict]) -> dict:
            _render_sidebar_brand()
            labels = [screen["title"] for screen in available_screens]
            selected_label = st.sidebar.pills("Navigation", labels, label_visibility="collapsed")
            if selected_label is None:
                selected_label = labels[0]
            return next(screen for screen in available_screens if screen["title"] == selected_label)""")

    if nav_style == 'top_pills':
        return sidebar_brand + textwrap.dedent("""
        def render_navigation(available_screens: list[dict]) -> dict:
            labels = [screen["title"] for screen in available_screens]
            selected_label = st.pills("Navigation", labels, label_visibility="collapsed")
            if selected_label is None:
                selected_label = labels[0]
            return next(screen for screen in available_screens if screen["title"] == selected_label)""")

    if nav_style == 'sidebar_segmented':
        return sidebar_brand + textwrap.dedent("""
        def render_navigation(available_screens: list[dict]) -> dict:
            _render_sidebar_brand()
            labels = [screen["title"] for screen in available_screens]
            selected_label = st.sidebar.segmented_control("Navigation", labels, label_visibility="collapsed")
            if selected_label is None:
                selected_label = labels[0]
            return next(screen for screen in available_screens if screen["title"] == selected_label)""")

    return sidebar_brand + textwrap.dedent("""
        def render_navigation(available_screens: list[dict]) -> dict:
            _render_sidebar_brand()
            labels = [screen["title"] for screen in available_screens]
            selected_label = st.sidebar.radio("Navigation", labels, label_visibility="collapsed")
            return next(screen for screen in available_screens if screen["title"] == selected_label)""")


def section_dashboard(spec: dict, theme: dict, profile: dict) -> str:
    layout = profile.get('dashboard_layout', 'metrics_grid')
    charts = profile.get('dashboard_charts', [])

    chart_helpers = _build_chart_helpers(charts)

    if layout == 'financial_kpi':
        return chart_helpers + _dashboard_financial_kpi()
    if layout == 'pipeline_funnel':
        return chart_helpers + _dashboard_pipeline_funnel()
    if layout == 'status_board':
        return chart_helpers + _dashboard_status_board()
    if layout == 'operations_hub':
        return chart_helpers + _dashboard_operations_hub()
    return chart_helpers + _dashboard_metrics_grid()


def _build_chart_helpers(charts: list[str]) -> str:
    parts = []
    if 'state_dist' in charts or 'state_bar' in charts:
        parts.append(textwrap.dedent("""\
        def _chart_state_distribution(entity: dict) -> None:
            records = fetch_records(entity)
            if not records or not workflow_enabled():
                return
            counts = {}
            for row in records:
                state = row["workflow_state"] or "Unknown"
                counts[state] = counts.get(state, 0) + 1
            st.bar_chart(counts)"""))

    if 'bar_totals' in charts:
        parts.append(textwrap.dedent("""\
        def _chart_bar_totals(entity: dict) -> None:
            records = fetch_records(entity)
            dec_field = first_decimal_field(entity)
            if not records or not dec_field or not workflow_enabled():
                return
            totals = {}
            for row in records:
                state = row["workflow_state"] or "Unknown"
                totals[state] = totals.get(state, 0) + (row[dec_field] or 0)
            st.bar_chart(totals)"""))

    if 'area_pipeline' in charts:
        parts.append(textwrap.dedent("""\
        def _chart_area_pipeline(entity: dict) -> None:
            records = fetch_records(entity)
            dec_field = first_decimal_field(entity)
            if not records or not workflow_enabled():
                return
            if dec_field:
                data = {}
                for row in records:
                    state = row["workflow_state"] or "Unknown"
                    data[state] = data.get(state, 0) + (row[dec_field] or 0)
            else:
                data = {}
                for row in records:
                    state = row["workflow_state"] or "Unknown"
                    data[state] = data.get(state, 0) + 1
            st.area_chart(data)"""))

    if 'line_trend' in charts:
        parts.append(textwrap.dedent("""\
        def _chart_line_trend(entity: dict) -> None:
            records = fetch_records(entity)
            date_field = first_date_field(entity)
            if not records or not date_field:
                return
            buckets = {}
            for row in records:
                d = row[date_field]
                if d:
                    buckets[d] = buckets.get(d, 0) + 1
            if buckets:
                st.line_chart(dict(sorted(buckets.items())))"""))

    if not parts:
        return ''
    return '\n\n'.join(parts) + '\n\n'


def _dashboard_metrics_grid() -> str:
    return (
        "def render_dashboard() -> None:\n"
        '    total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])\n'
        "    render_screen_header(\n"
        '        SPEC["name"],\n'
        '        SPEC["description"] or "Generated operational prototype for rapid validation and internal walkthroughs.",\n'
        '        THEME["label"],\n'
        "        [\n"
        "            f'{len(SPEC[\"entities\"])} entities',\n"
        "            f'{len(SPEC[\"screens\"])} screens',\n"
        "            f'{total_records} saved records',\n"
        "        ],\n"
        "    )\n"
        "    metric_columns = st.columns(4)\n"
        "    with metric_columns[0]:\n"
        '        st.metric("Entities", len(SPEC["entities"]))\n'
        "    with metric_columns[1]:\n"
        '        st.metric("Screens", len(SPEC["screens"]))\n'
        "    with metric_columns[2]:\n"
        '        st.metric("Workflow states", len(SPEC["workflow_states"]))\n'
        "    with metric_columns[3]:\n"
        '        st.metric("Stored records", total_records)\n'
        "\n"
        '    entity_columns = st.columns(max(1, min(3, len(SPEC["entities"]) or 1)))\n'
        '    for index, entity in enumerate(SPEC["entities"]):\n'
        "        records = fetch_records(entity)\n"
        "        with entity_columns[index % len(entity_columns)]:\n"
        "            st.markdown(\n"
        f"                f{TQ}\n"
        '                <div class="entity-card">\n'
        '                    <p>{entity["plural_name"]}</p>\n'
        "                    <strong>{len(records)}</strong>\n"
        '                    <span>{len(entity["fields"])} fields configured</span>\n'
        '                    <p>{entity["description"] or "No description yet."}</p>\n'
        "                </div>\n"
        f"                {TQ},\n"
        "                unsafe_allow_html=True,\n"
        "            )\n"
        "\n"
        '    if SPEC["workflow_states"]:\n'
        "        st.markdown('<p class=\"section-label\">Workflow path</p>', unsafe_allow_html=True)\n"
        "        render_workflow_strip()\n"
        "\n"
        '    if SPEC["screens"]:\n'
        "        st.markdown('<p class=\"section-label\">Generated views</p>', unsafe_allow_html=True)\n"
        '        screen_columns = st.columns(max(1, min(4, len(SPEC["screens"]) or 1)))\n'
        '        for index, screen in enumerate(SPEC["screens"]):\n'
        "            with screen_columns[index % len(screen_columns)]:\n"
        '                subtitle = screen["screen_type"].replace("_", " ").title()\n'
        '                if screen.get("entity"):\n'
        "                    subtitle += f' for {get_entity(screen[\"entity\"])[\"name\"]}'\n"
        "                st.markdown(\n"
        f"                    f{TQ}\n"
        '                    <div class="info-panel compact-panel">\n'
        '                        <span>{screen["title"]}</span>\n'
        "                        <strong>{subtitle}</strong>\n"
        "                    </div>\n"
        f"                    {TQ},\n"
        "                    unsafe_allow_html=True,\n"
        "                )\n"
    )


def _dashboard_financial_kpi() -> str:
    return textwrap.dedent("""\
        def render_dashboard() -> None:
            total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])
            render_screen_header(
                SPEC["name"],
                SPEC["description"] or "Financial overview with key performance indicators.",
                THEME["label"],
                [
                    f'{len(SPEC["entities"])} entities',
                    f'{total_records} saved records',
                ],
            )
            total_value = 0.0
            primary_entity = SPEC["entities"][0] if SPEC["entities"] else None
            primary_records = []
            if primary_entity:
                primary_records = fetch_records(primary_entity)
                dec_field = first_decimal_field(primary_entity)
                if dec_field:
                    total_value = sum(row[dec_field] or 0 for row in primary_records)

            kpi_cols = st.columns(3)
            with kpi_cols[0]:
                st.metric("Total value", f"${total_value:,.2f}")
            with kpi_cols[1]:
                st.metric("Total records", total_records)
            with kpi_cols[2]:
                avg = total_value / len(primary_records) if primary_records else 0
                st.metric("Average", f"${avg:,.2f}")

            if primary_entity and primary_records:
                chart_cols = st.columns(2)
                with chart_cols[0]:
                    st.markdown('<p class="section-label">Totals by state</p>', unsafe_allow_html=True)
                    _chart_bar_totals(primary_entity)
                with chart_cols[1]:
                    st.markdown('<p class="section-label">Records by state</p>', unsafe_allow_html=True)
                    _chart_state_distribution(primary_entity)

            if primary_entity and primary_records:
                with st.expander(f"Recent {primary_entity['plural_name']}", expanded=False):
                    recent = primary_records[:5]
                    st.dataframe(
                        [serialize_record(primary_entity, row) for row in recent],
                        use_container_width=True,
                        hide_index=True,
                    )

            entity_columns = st.columns(max(1, min(3, len(SPEC["entities"]) or 1)))
            for index, entity in enumerate(SPEC["entities"]):
                records = fetch_records(entity)
                with entity_columns[index % len(entity_columns)]:
                    with st.container(border=True):
                        st.markdown(f"**{entity['plural_name']}**")
                        st.caption(f"{len(records)} records | {len(entity['fields'])} fields")
                        st.caption(entity["description"] or "No description yet.")""")


def _dashboard_pipeline_funnel() -> str:
    return textwrap.dedent("""\
        def render_dashboard() -> None:
            total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])
            render_screen_header(
                SPEC["name"],
                SPEC["description"] or "Pipeline overview with funnel metrics and value tracking.",
                THEME["label"],
                [
                    f'{len(SPEC["entities"])} entities',
                    f'{total_records} saved records',
                ],
            )
            if workflow_enabled():
                state_cols = st.columns(len(SPEC["workflow_states"]))
                for idx, state in enumerate(SPEC["workflow_states"]):
                    count = 0
                    for entity in SPEC["entities"]:
                        for row in fetch_records(entity):
                            if row["workflow_state"] == state["name"]:
                                count += 1
                    with state_cols[idx]:
                        st.metric(state["name"], count)

            primary_entity = SPEC["entities"][0] if SPEC["entities"] else None
            if primary_entity:
                primary_records = fetch_records(primary_entity)
                if primary_records:
                    chart_cols = st.columns(2)
                    with chart_cols[0]:
                        st.markdown('<p class="section-label">Pipeline values</p>', unsafe_allow_html=True)
                        _chart_area_pipeline(primary_entity)
                    with chart_cols[1]:
                        st.markdown('<p class="section-label">State distribution</p>', unsafe_allow_html=True)
                        _chart_state_distribution(primary_entity)

                    st.markdown('<p class="section-label">Top records</p>', unsafe_allow_html=True)
                    top_records = primary_records[:5]
                    top_cols = st.columns(min(3, len(top_records)))
                    for idx, row in enumerate(top_records):
                        with top_cols[idx % len(top_cols)]:
                            with st.container(border=True):
                                st.markdown(f"**{format_record_title(primary_entity, row)}**")
                                if workflow_enabled():
                                    st.badge(row["workflow_state"])
                                dec_field = first_decimal_field(primary_entity)
                                if dec_field and row[dec_field]:
                                    st.caption(f"Value: ${row[dec_field]:,.2f}")

            entity_strip = st.columns(max(1, min(4, len(SPEC["entities"]) or 1)))
            for idx, entity in enumerate(SPEC["entities"]):
                with entity_strip[idx % len(entity_strip)]:
                    st.metric(entity["plural_name"], len(fetch_records(entity)))""")


def _dashboard_status_board() -> str:
    return textwrap.dedent("""\
        def render_dashboard() -> None:
            total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])
            render_screen_header(
                SPEC["name"],
                SPEC["description"] or "Status board organized by workflow state.",
                THEME["label"],
                [
                    f'{len(SPEC["entities"])} entities',
                    f'{total_records} saved records',
                ],
            )
            if workflow_enabled():
                state_cols = st.columns(len(SPEC["workflow_states"]))
                all_records = []
                for entity in SPEC["entities"]:
                    for row in fetch_records(entity):
                        all_records.append((entity, row))
                for idx, state in enumerate(SPEC["workflow_states"]):
                    with state_cols[idx]:
                        state_records = [(e, r) for e, r in all_records if r["workflow_state"] == state["name"]]
                        st.badge(f'{state["name"]} ({len(state_records)})')
                        for entity, row in state_records[:8]:
                            with st.container(border=True):
                                st.markdown(f"**{format_record_title(entity, row)}**")
                                st.caption(f'{entity["name"]} #{row["id"]}')

                st.markdown('<p class="section-label">State distribution</p>', unsafe_allow_html=True)
                for entity in SPEC["entities"]:
                    _chart_state_distribution(entity)

            metric_cols = st.columns(max(1, min(4, len(SPEC["entities"]) or 1)))
            for idx, entity in enumerate(SPEC["entities"]):
                with metric_cols[idx % len(metric_cols)]:
                    st.metric(entity["plural_name"], len(fetch_records(entity)))""")


def _dashboard_operations_hub() -> str:
    return textwrap.dedent("""\
        def render_dashboard() -> None:
            total_records = sum(len(fetch_records(entity)) for entity in SPEC["entities"])
            render_screen_header(
                SPEC["name"],
                SPEC["description"] or "Operations hub with urgency metrics and activity tracking.",
                THEME["label"],
                [
                    f'{len(SPEC["entities"])} entities',
                    f'{total_records} saved records',
                ],
            )
            if workflow_enabled():
                state_cols = st.columns(len(SPEC["workflow_states"]))
                for idx, state in enumerate(SPEC["workflow_states"]):
                    count = 0
                    for entity in SPEC["entities"]:
                        for row in fetch_records(entity):
                            if row["workflow_state"] == state["name"]:
                                count += 1
                    with state_cols[idx]:
                        st.metric(state["name"], count)

            primary_entity = SPEC["entities"][0] if SPEC["entities"] else None
            if primary_entity:
                primary_records = fetch_records(primary_entity)
                if primary_records:
                    chart_cols = st.columns(2)
                    with chart_cols[0]:
                        st.markdown('<p class="section-label">Volume trend</p>', unsafe_allow_html=True)
                        _chart_line_trend(primary_entity)
                    with chart_cols[1]:
                        st.markdown('<p class="section-label">State distribution</p>', unsafe_allow_html=True)
                        _chart_state_distribution(primary_entity)

                    with st.expander("Recent activity", expanded=False):
                        recent = primary_records[:5]
                        for row in recent:
                            title = format_record_title(primary_entity, row)
                            state = row["workflow_state"] if workflow_enabled() else ""
                            st.markdown(f"- **{title}** {f'({state})' if state else ''}")

            entity_columns = st.columns(max(1, min(3, len(SPEC["entities"]) or 1)))
            for index, entity in enumerate(SPEC["entities"]):
                records = fetch_records(entity)
                with entity_columns[index % len(entity_columns)]:
                    with st.container(border=True):
                        st.markdown(f"**{entity['plural_name']}**")
                        st.caption(f"{len(records)} records | {len(entity['fields'])} fields")""")


def section_list_screen(spec: dict, theme: dict, profile: dict) -> str:
    list_style = profile.get('list_style', 'dataframe')
    use_download = profile.get('use_download', False)
    use_column_config = profile.get('list_column_config', False)

    if list_style == 'grouped_expanders':
        return _list_grouped_expanders()
    if list_style == 'rich_dataframe':
        return _list_rich_dataframe(use_column_config, use_download)
    return _list_plain_dataframe()


def _list_plain_dataframe() -> str:
    return textwrap.dedent("""\
        def render_list_screen(screen: dict) -> None:
            entity = get_entity(screen["entity"])
            records = fetch_records(entity)
            render_screen_header(
                screen["title"],
                entity["description"] or f'Review and scan {entity["plural_name"].lower()} in one place.',
                f'{entity["plural_name"]} list',
                [f'{len(records)} records', f'{len(list_fields_for_entity(entity))} list columns'],
            )
            if not records:
                render_empty_state(
                    f'No {entity["plural_name"].lower()} yet',
                    f'Add the first {entity["name"].lower()} from the form screen to populate this list.',
                )
                return

            search_col, filter_col, summary_col = st.columns([1.4, 1.0, 0.7])
            query = search_col.text_input(
                "Search records",
                value="",
                placeholder=f'Search {entity["plural_name"].lower()}',
            )
            state_filter = "All states"
            if workflow_enabled():
                state_filter = filter_col.selectbox(
                    "Workflow state",
                    options=["All states"] + [state["name"] for state in SPEC["workflow_states"]],
                )
            with summary_col:
                filtered = [
                    row
                    for row in records
                    if (state_filter == "All states" or row["workflow_state"] == state_filter)
                    and row_matches_query(entity, row, query)
                ]
                st.metric("Showing", len(filtered))

            if not filtered:
                render_empty_state(
                    "No matching records",
                    "Change the search query or workflow filter to see saved records again.",
                )
                return

            render_record_glance_cards(entity, filtered)
            st.dataframe(
                [serialize_record(entity, row) for row in filtered],
                use_container_width=True,
                hide_index=True,
            )""")


def _list_rich_dataframe(use_column_config: bool, use_download: bool) -> str:
    config_arg = ''
    if use_column_config:
        config_arg = '\n        column_config=build_column_config(entity),'

    download_block = ''
    if use_download:
        download_block = (
            "\n"
            '    csv_data = records_to_csv(entity, filtered)\n'
            "    if csv_data:\n"
            "        st.download_button(\n"
            '            "Download CSV",\n'
            "            data=csv_data,\n"
            "            file_name=f'{entity[\"slug\"]}_export.csv',\n"
            '            mime="text/csv",\n'
            "        )"
        )

    return textwrap.dedent("""\
        def render_list_screen(screen: dict) -> None:
            entity = get_entity(screen["entity"])
            records = fetch_records(entity)
            render_screen_header(
                screen["title"],
                entity["description"] or f'Review and scan {entity["plural_name"].lower()} in one place.',
                f'{entity["plural_name"]} list',
                [f'{len(records)} records', f'{len(list_fields_for_entity(entity))} list columns'],
            )
            if not records:
                render_empty_state(
                    f'No {entity["plural_name"].lower()} yet',
                    f'Add the first {entity["name"].lower()} from the form screen to populate this list.',
                )
                return

            search_col, filter_col, summary_col = st.columns([1.4, 1.0, 0.7])
            query = search_col.text_input(
                "Search records",
                value="",
                placeholder=f'Search {entity["plural_name"].lower()}',
            )
            state_filter = "All states"
            if workflow_enabled():
                state_filter = filter_col.selectbox(
                    "Workflow state",
                    options=["All states"] + [state["name"] for state in SPEC["workflow_states"]],
                )
            with summary_col:
                filtered = [
                    row
                    for row in records
                    if (state_filter == "All states" or row["workflow_state"] == state_filter)
                    and row_matches_query(entity, row, query)
                ]
                st.metric("Showing", len(filtered))

            if not filtered:
                render_empty_state(
                    "No matching records",
                    "Change the search query or workflow filter to see saved records again.",
                )
                return

            dec_field = first_decimal_field(entity)
            if dec_field:
                total = sum(row[dec_field] or 0 for row in filtered)
                st.metric(f"Total {entity['plural_name']} value", f"${total:,.2f}")

            st.dataframe(
                [serialize_record(entity, row) for row in filtered],
                use_container_width=True,
                hide_index=True,""") + config_arg + "\n    )" + download_block


def _list_grouped_expanders() -> str:
    return textwrap.dedent("""\
        def render_list_screen(screen: dict) -> None:
            entity = get_entity(screen["entity"])
            records = fetch_records(entity)
            render_screen_header(
                screen["title"],
                entity["description"] or f'Review and scan {entity["plural_name"].lower()} in one place.',
                f'{entity["plural_name"]} list',
                [f'{len(records)} records'],
            )
            if not records:
                render_empty_state(
                    f'No {entity["plural_name"].lower()} yet',
                    f'Add the first {entity["name"].lower()} from the form screen to populate this list.',
                )
                return

            search_col, summary_col = st.columns([1.6, 0.5])
            query = search_col.text_input(
                "Search records",
                value="",
                placeholder=f'Search {entity["plural_name"].lower()}',
            )
            filtered = [row for row in records if row_matches_query(entity, row, query)]
            with summary_col:
                st.metric("Showing", len(filtered))

            if not filtered:
                render_empty_state(
                    "No matching records",
                    "Change the search query to see saved records again.",
                )
                return

            if workflow_enabled():
                for state in SPEC["workflow_states"]:
                    group = [row for row in filtered if row["workflow_state"] == state["name"]]
                    with st.expander(f'{state["name"]} ({len(group)})', expanded=len(group) > 0):
                        if group:
                            st.dataframe(
                                [serialize_record(entity, row) for row in group],
                                use_container_width=True,
                                hide_index=True,
                                column_config=build_column_config(entity),
                            )
                        else:
                            st.caption("No records in this state.")
            else:
                render_record_glance_cards(entity, filtered)
                st.dataframe(
                    [serialize_record(entity, row) for row in filtered],
                    use_container_width=True,
                    hide_index=True,
                    column_config=build_column_config(entity),
                )""")


def section_detail_screen(spec: dict, theme: dict, profile: dict) -> str:
    detail_style = profile.get('detail_style', 'two_column')
    use_badges = profile.get('use_badges', False)

    if detail_style == 'tabbed':
        return _detail_tabbed(use_badges)
    return _detail_two_column()


def _detail_two_column() -> str:
    return (
        "def render_detail_screen(screen: dict) -> None:\n"
        '    entity = get_entity(screen["entity"])\n'
        "    records = fetch_records(entity)\n"
        "    render_screen_header(\n"
        '        screen["title"],\n'
        "        entity[\"description\"] or f'Inspect a single {entity[\"name\"].lower()} record and its current state.',\n"
        "        f'{entity[\"name\"]} detail',\n"
        "        [f'{len(records)} available records'],\n"
        "    )\n"
        "    if not records:\n"
        "        render_empty_state(\n"
        "            f'No {entity[\"plural_name\"].lower()} available',\n"
        "            f'Add a {entity[\"name\"].lower()} record before opening the detail view.',\n"
        "        )\n"
        "        return\n"
        "\n"
        "    selector_col, context_col = st.columns([1.1, 0.9])\n"
        '    ids = [row["id"] for row in records]\n'
        "    record_id = selector_col.selectbox(\n"
        '        "Select record",\n'
        "        options=ids,\n"
        "        format_func=lambda value: format_record_title(\n"
        "            entity,\n"
        '            next(row for row in records if row["id"] == value),\n'
        "        ),\n"
        "    )\n"
        '    selected = next(row for row in records if row["id"] == record_id)\n'
        "    payload = serialize_record(entity, selected)\n"
        "\n"
        "    with context_col:\n"
        "        st.markdown(\n"
        f"            f{TQ}\n"
        '            <div class="info-panel">\n'
        "                <span>Current record</span>\n"
        "                <strong>{format_record_title(entity, selected)}</strong>\n"
        "                <p>Record #{record_id}</p>\n"
        "            </div>\n"
        f"            {TQ},\n"
        "            unsafe_allow_html=True,\n"
        "        )\n"
        '        if "State" in payload:\n'
        "            st.markdown(\n"
        f"                f{TQ}\n"
        '                <div class="info-panel compact-panel">\n'
        "                    <span>Workflow state</span>\n"
        '                    <strong>{payload["State"]}</strong>\n'
        "                </div>\n"
        f"                {TQ},\n"
        "                unsafe_allow_html=True,\n"
        "            )\n"
        "\n"
        "    detail_columns = st.columns(2)\n"
        "    visible_items = [\n"
        "        (label, value)\n"
        "        for label, value in payload.items()\n"
        '        if label not in {"ID", "State"}\n'
        "    ]\n"
        "    for index, (label, value) in enumerate(visible_items):\n"
        "        with detail_columns[index % 2]:\n"
        "            st.markdown(\n"
        f"                f{TQ}\n"
        '                <div class="detail-card">\n'
        "                    <span>{label}</span>\n"
        "                    <strong>{format_display_value(value)}</strong>\n"
        "                </div>\n"
        f"                {TQ},\n"
        "                unsafe_allow_html=True,\n"
        "            )\n"
    )


def _detail_tabbed(use_badges: bool) -> str:
    state_display = ""
    if use_badges:
        state_display = (
            '        if "State" in payload:\n'
            '            st.badge(payload["State"])\n'
        )
    else:
        state_display = (
            '        if "State" in payload:\n'
            "            st.markdown(\n"
            f"                f{TQ}\n"
            '                <div class="info-panel compact-panel">\n'
            "                    <span>Workflow state</span>\n"
            '                    <strong>{payload["State"]}</strong>\n'
            "                </div>\n"
            f"                {TQ},\n"
            "                unsafe_allow_html=True,\n"
            "            )\n"
        )

    return (
        "def render_detail_screen(screen: dict) -> None:\n"
        '    entity = get_entity(screen["entity"])\n'
        "    records = fetch_records(entity)\n"
        "    render_screen_header(\n"
        '        screen["title"],\n'
        "        entity[\"description\"] or f'Inspect a single {entity[\"name\"].lower()} record and its current state.',\n"
        "        f'{entity[\"name\"]} detail',\n"
        "        [f'{len(records)} available records'],\n"
        "    )\n"
        "    if not records:\n"
        "        render_empty_state(\n"
        "            f'No {entity[\"plural_name\"].lower()} available',\n"
        "            f'Add a {entity[\"name\"].lower()} record before opening the detail view.',\n"
        "        )\n"
        "        return\n"
        "\n"
        "    selector_col, context_col = st.columns([1.1, 0.9])\n"
        '    ids = [row["id"] for row in records]\n'
        "    record_id = selector_col.selectbox(\n"
        '        "Select record",\n'
        "        options=ids,\n"
        "        format_func=lambda value: format_record_title(\n"
        "            entity,\n"
        '            next(row for row in records if row["id"] == value),\n'
        "        ),\n"
        "    )\n"
        '    selected = next(row for row in records if row["id"] == record_id)\n'
        "    payload = serialize_record(entity, selected)\n"
        "\n"
        "    with context_col:\n"
        "        st.markdown(\n"
        f"            f{TQ}\n"
        '            <div class="info-panel">\n'
        "                <span>Current record</span>\n"
        "                <strong>{format_record_title(entity, selected)}</strong>\n"
        "                <p>Record #{record_id}</p>\n"
        "            </div>\n"
        f"            {TQ},\n"
        "            unsafe_allow_html=True,\n"
        "        )\n"
        "\n"
        '    related_entities = find_related_entities(entity["slug"])\n'
        '    tab_labels = ["Details"] + [rel["entity"]["plural_name"] for rel in related_entities]\n'
        "    tabs = st.tabs(tab_labels)\n"
        "\n"
        "    with tabs[0]:\n"
        + state_display
        + "        detail_columns = st.columns(2)\n"
        "        visible_items = [\n"
        "            (label, value)\n"
        "            for label, value in payload.items()\n"
        '            if label not in {"ID", "State"}\n'
        "        ]\n"
        "        for index, (label, value) in enumerate(visible_items):\n"
        "            with detail_columns[index % 2]:\n"
        "                st.markdown(\n"
        f"                    f{TQ}\n"
        '                    <div class="detail-card">\n'
        "                        <span>{label}</span>\n"
        "                        <strong>{format_display_value(value)}</strong>\n"
        "                    </div>\n"
        f"                    {TQ},\n"
        "                    unsafe_allow_html=True,\n"
        "                )\n"
        "\n"
        "    for tab_idx, rel in enumerate(related_entities, start=1):\n"
        "        with tabs[tab_idx]:\n"
        '            rel_entity = rel["entity"]\n'
        '            rel_field = rel["field"]\n'
        "            rel_records = fetch_records(rel_entity)\n"
        '            linked = [r for r in rel_records if r[rel_field["name"]] == record_id]\n'
        "            if linked:\n"
        "                st.dataframe(\n"
        "                    [serialize_record(rel_entity, r) for r in linked],\n"
        "                    use_container_width=True,\n"
        "                    hide_index=True,\n"
        "                    column_config=build_column_config(rel_entity),\n"
        "                )\n"
        "            else:\n"
        "                st.caption(f'No {rel_entity[\"plural_name\"].lower()} linked to this record.')\n"
    )


def section_form_screen(spec: dict, theme: dict, profile: dict) -> str:
    form_style = profile.get('form_style', 'inline')

    if form_style == 'dialog_create':
        return _form_dialog_create()
    return _form_inline()


def _render_form_fields_code() -> str:
    """Generate the _render_form_fields function code, shared by both inline and dialog forms."""
    return (
        "def _render_form_fields(entity: dict, selected_row, selected_id, dialog_mode: bool = False) -> None:\n"
        "    key_prefix = f'{entity[\"slug\"]}_{selected_id or \"new\"}'\n"
        "    payload = hydrate_calculated_fields(\n"
        "        entity,\n"
        "        collect_current_values(entity, selected_row, key_prefix),\n"
        "    )\n"
        "    visible_field_names = set()\n"
        "    hidden_field_count = 0\n"
        "    calculated_field_labels = []\n"
        '    form_col, side_col = st.columns([0.7, 0.3], gap="large")\n'
        "\n"
        "    if workflow_enabled():\n"
        "        with side_col:\n"
        '            states = [state["name"] for state in SPEC["workflow_states"]]\n'
        '            default_value = selected_row["workflow_state"] if selected_row else default_state()\n'
        '            state_key = widget_key(key_prefix, "workflow_state")\n'
        "            current_state = st.session_state.get(state_key, default_value)\n"
        "            payload[\"workflow_state\"] = st.selectbox(\n"
        '                "Workflow state",\n'
        "                options=states,\n"
        "                index=states.index(current_state) if current_state in states else 0,\n"
        "                key=state_key,\n"
        "            )\n"
        "\n"
        "    field_columns = form_col.columns(2)\n"
        "    column_index = 0\n"
        '    for field in entity["fields"]:\n'
        "        payload = hydrate_calculated_fields(entity, payload)\n"
        "        if not field_is_visible(field, payload):\n"
        "            hidden_field_count += 1\n"
        "            continue\n"
        '        visible_field_names.add(field["name"])\n'
        '        if field.get("is_calculated"):\n'
        '            calculated_field_labels.append(field["label"])\n'
        "            with form_col:\n"
        "                with st.container(border=True):\n"
        '                    calc_value = payload.get(field["name"])\n'
        "                    if isinstance(calc_value, (int, float)):\n"
        '                        st.metric(field["label"], f"{calc_value:,.2f}" if isinstance(calc_value, float) else str(calc_value))\n'
        "                    else:\n"
        "                        st.markdown(\n"
        f"                            f{TQ}\n"
        '                            <div class="readout-card">\n'
        '                                <span>{field["label"]}</span>\n'
        "                                <strong>{format_display_value(calc_value)}</strong>\n"
        '                                <p>{field.get("help_text") or "Calculated automatically from the current inputs."}</p>\n'
        "                            </div>\n"
        f"                            {TQ},\n"
        "                            unsafe_allow_html=True,\n"
        "                        )\n"
        "            continue\n"
        "\n"
        '        target_container = form_col if field["field_type"] == "long_text" else field_columns[column_index % 2]\n'
        '        if field["field_type"] != "long_text":\n'
        "            column_index += 1\n"
        "        with target_container:\n"
        '            payload[field["name"]] = render_field_input(\n'
        "                field,\n"
        '                payload.get(field["name"]),\n'
        "                key_prefix,\n"
        "            )\n"
        "\n"
        "    payload = hydrate_calculated_fields(entity, payload)\n"
        "\n"
        "    with side_col:\n"
        "        st.markdown(\n"
        f"            f{TQ}\n"
        '            <div class="info-panel">\n'
        "                <span>Form coverage</span>\n"
        "                <strong>{len(visible_field_names)} visible fields</strong>\n"
        "                <p>{hidden_field_count} hidden by rules</p>\n"
        "            </div>\n"
        f"            {TQ},\n"
        "            unsafe_allow_html=True,\n"
        "        )\n"
        "        if calculated_field_labels:\n"
        "            calculated_html = \"\".join(f'<li>{label}</li>' for label in calculated_field_labels)\n"
        "            st.markdown(\n"
        f"                f{TQ}\n"
        '                <div class="info-panel">\n'
        "                    <span>Dynamic fields</span>\n"
        "                    <strong>{len(calculated_field_labels)} calculated outputs</strong>\n"
        '                    <ul class="plain-list">{calculated_html}</ul>\n'
        "                </div>\n"
        f"                {TQ},\n"
        "                unsafe_allow_html=True,\n"
        "            )\n"
        "        if workflow_enabled():\n"
        "            render_workflow_strip()\n"
        "\n"
        "    with form_col:\n"
        '        submitted = st.button("Save record", type="primary", use_container_width=True)\n'
        "\n"
        "    if submitted:\n"
        "        missing = [\n"
        '            field["label"]\n'
        '            for field in entity["fields"]\n'
        '            if field["name"] in visible_field_names and field["required"] and payload.get(field["name"]) in (None, "", [])\n'
        "        ]\n"
        "        if missing:\n"
        '            st.error("Missing required fields: " + ", ".join(missing))\n'
        "            return\n"
        "        validation_errors = []\n"
        '        for field in entity["fields"]:\n'
        '            if field["name"] not in visible_field_names:\n'
        "                continue\n"
        "            expression = (field.get(\"validation_expression\") or \"\").strip()\n"
        "            if not expression:\n"
        "                continue\n"
        "            context = dict(payload)\n"
        '            context["value"] = payload.get(field["name"])\n'
        "            is_valid = bool(safe_rule_value(expression, context, False))\n"
        "            if not is_valid:\n"
        "                validation_errors.append(\n"
        "                    field.get(\"validation_message\") or f'{field[\"label\"]} failed validation.'\n"
        "                )\n"
        "        if validation_errors:\n"
        "            for message in validation_errors:\n"
        "                st.error(message)\n"
        "            return\n"
        "        if selected_row:\n"
        '            update_record(entity, selected_row["id"], payload)\n'
        "            clear_form_state(entity, key_prefix)\n"
        "            notify_success(f'Updated {entity[\"name\"]} #{selected_row[\"id\"]}')\n"
        "        else:\n"
        "            insert_record(entity, payload)\n"
        "            clear_form_state(entity, key_prefix)\n"
        "            notify_success(f'Created a new {entity[\"name\"].lower()} record')\n"
        "        st.rerun()\n"
    )


def _form_inline() -> str:
    return (
        "def render_form_screen(screen: dict) -> None:\n"
        '    entity = get_entity(screen["entity"])\n'
        "    records = fetch_records(entity)\n"
        "    render_screen_header(\n"
        '        screen["title"],\n'
        "        entity[\"description\"] or f'Create or update {entity[\"plural_name\"].lower()} while preserving prototype rules and workflow state.',\n"
        "        f'{entity[\"name\"]} editor',\n"
        "        [\n"
        "            f'{len(records)} saved records',\n"
        "            f'{sum(1 for field in entity[\"fields\"] if field.get(\"is_calculated\"))} calculated fields',\n"
        "        ],\n"
        "    )\n"
        "\n"
        '    mode_col, target_col = st.columns([0.8, 1.2])\n'
        '    mode = mode_col.radio("Mode", options=["Create new", "Edit existing"], horizontal=True)\n'
        "    selected_row = None\n"
        "    selected_id = None\n"
        '    if mode == "Edit existing":\n'
        "        if not records:\n"
        "            render_empty_state(\n"
        '                "No records to edit yet",\n'
        "                f'Create the first {entity[\"name\"].lower()} record before switching into edit mode.',\n"
        "            )\n"
        "            return\n"
        '        ids = [row["id"] for row in records]\n'
        "        selected_id = target_col.selectbox(\n"
        '            "Record",\n'
        "            options=ids,\n"
        "            format_func=lambda value: format_record_title(\n"
        "                entity,\n"
        '                next(row for row in records if row["id"] == value),\n'
        "            ),\n"
        "        )\n"
        '        selected_row = next(row for row in records if row["id"] == selected_id)\n'
        "    else:\n"
        "        target_col.markdown(\n"
        f"            {TQ}\n"
        '            <div class="info-panel compact-panel">\n'
        "                <span>Create mode</span>\n"
        "                <strong>New record</strong>\n"
        "                <p>Fill the fields below to create a fresh record from the current schema.</p>\n"
        "            </div>\n"
        f"            {TQ},\n"
        "            unsafe_allow_html=True,\n"
        "        )\n"
        "\n"
        "    _render_form_fields(entity, selected_row, selected_id)\n"
        "\n\n"
        + _render_form_fields_code()
    )


def _form_dialog_create() -> str:
    return (
        "def render_form_screen(screen: dict) -> None:\n"
        '    entity = get_entity(screen["entity"])\n'
        "    records = fetch_records(entity)\n"
        "    render_screen_header(\n"
        '        screen["title"],\n'
        "        entity[\"description\"] or f'Create or update {entity[\"plural_name\"].lower()} while preserving prototype rules and workflow state.',\n"
        "        f'{entity[\"name\"]} editor',\n"
        "        [\n"
        "            f'{len(records)} saved records',\n"
        "            f'{sum(1 for field in entity[\"fields\"] if field.get(\"is_calculated\"))} calculated fields',\n"
        "        ],\n"
        "    )\n"
        "\n"
        '    if st.button("Create new", type="primary"):\n'
        "        _open_create_dialog(entity)\n"
        "\n"
        "    if records:\n"
        "        st.markdown('<p class=\"section-label\">Edit existing record</p>', unsafe_allow_html=True)\n"
        '        ids = [row["id"] for row in records]\n'
        "        selected_id = st.selectbox(\n"
        '            "Record",\n'
        "            options=ids,\n"
        "            format_func=lambda value: format_record_title(\n"
        "                entity,\n"
        '                next(row for row in records if row["id"] == value),\n'
        "            ),\n"
        "        )\n"
        '        selected_row = next(row for row in records if row["id"] == selected_id)\n'
        "        _render_form_fields(entity, selected_row, selected_id)\n"
        "\n\n"
        '@st.dialog("Create new record", width="large")\n'
        "def _open_create_dialog(entity: dict) -> None:\n"
        "    _render_dialog_form_fields(entity)\n"
        "\n\n"
        "def _render_dialog_form_fields(entity: dict) -> None:\n"
        '    key_prefix = f\'{entity["slug"]}_dialog_new\'\n'
        "    payload = hydrate_calculated_fields(\n"
        "        entity,\n"
        "        collect_current_values(entity, None, key_prefix),\n"
        "    )\n"
        "    visible_field_names = set()\n"
        "\n"
        "    if workflow_enabled():\n"
        '        states = [state["name"] for state in SPEC["workflow_states"]]\n'
        '        state_key = widget_key(key_prefix, "workflow_state")\n'
        "        current_state = st.session_state.get(state_key, default_state())\n"
        "        payload[\"workflow_state\"] = st.selectbox(\n"
        '            "Workflow state",\n'
        "            options=states,\n"
        "            index=states.index(current_state) if current_state in states else 0,\n"
        "            key=state_key,\n"
        "        )\n"
        "\n"
        '    for field in entity["fields"]:\n'
        "        payload = hydrate_calculated_fields(entity, payload)\n"
        "        if not field_is_visible(field, payload):\n"
        "            continue\n"
        '        visible_field_names.add(field["name"])\n'
        '        if field.get("is_calculated"):\n'
        '            calc_value = payload.get(field["name"])\n'
        "            if isinstance(calc_value, (int, float)):\n"
        '                st.metric(field["label"], f"{calc_value:,.2f}" if isinstance(calc_value, float) else str(calc_value))\n'
        "            else:\n"
        "                st.markdown(f\"**{field['label']}**: {format_display_value(calc_value)}\")\n"
        "            continue\n"
        '        payload[field["name"]] = render_field_input(\n'
        "            field,\n"
        '            payload.get(field["name"]),\n'
        "            key_prefix,\n"
        "        )\n"
        "\n"
        "    payload = hydrate_calculated_fields(entity, payload)\n"
        "\n"
        '    if st.button("Save", type="primary", use_container_width=True, key="dialog_save"):\n'
        "        missing = [\n"
        '            field["label"]\n'
        '            for field in entity["fields"]\n'
        '            if field["name"] in visible_field_names and field["required"] and payload.get(field["name"]) in (None, "", [])\n'
        "        ]\n"
        "        if missing:\n"
        '            st.error("Missing required fields: " + ", ".join(missing))\n'
        "            return\n"
        "        validation_errors = []\n"
        '        for field in entity["fields"]:\n'
        '            if field["name"] not in visible_field_names:\n'
        "                continue\n"
        "            expression = (field.get(\"validation_expression\") or \"\").strip()\n"
        "            if not expression:\n"
        "                continue\n"
        "            context = dict(payload)\n"
        '            context["value"] = payload.get(field["name"])\n'
        "            is_valid = bool(safe_rule_value(expression, context, False))\n"
        "            if not is_valid:\n"
        "                validation_errors.append(\n"
        "                    field.get(\"validation_message\") or f'{field[\"label\"]} failed validation.'\n"
        "                )\n"
        "        if validation_errors:\n"
        "            for message in validation_errors:\n"
        "                st.error(message)\n"
        "            return\n"
        "        insert_record(entity, payload)\n"
        "        clear_form_state(entity, key_prefix)\n"
        "        notify_success(f'Created a new {entity[\"name\"].lower()} record')\n"
        "        st.rerun()\n"
        "\n\n"
        + _render_form_fields_code()
    )


def section_screen_router() -> str:
    return textwrap.dedent("""\
        def render_screen(screen: dict) -> None:
            if screen["screen_type"] == "dashboard":
                render_dashboard()
            elif screen["screen_type"] == "list":
                render_list_screen(screen)
            elif screen["screen_type"] == "detail":
                render_detail_screen(screen)
            elif screen["screen_type"] == "form":
                render_form_screen(screen)""")


def section_css(theme: dict, profile: dict) -> str:
    css_content = build_css(theme, profile)
    return (
        "st.markdown(\n"
        f"    {TQ}\n"
        "    <style>\n"
        f"    {css_content}\n"
        "    </style>\n"
        f"    {TQ},\n"
        "    unsafe_allow_html=True,\n"
        ")"
    )


def section_main(spec: dict, profile: dict) -> str:
    logo_emoji = profile.get('logo_emoji')

    logo_line = ''
    if logo_emoji:
        logo_line = f'\nst.sidebar.markdown("# {logo_emoji}")'

    return (
        "st.set_page_config(page_title=f'{SPEC[\"name\"]} Prototype', layout='wide')\n"
        "ensure_database()"
        + logo_line
        + "\n\n"
        "available_screens = [screen for screen in SPEC[\"screens\"] if screen.get(\"include_in_navigation\", True)]\n"
        "if not available_screens:\n"
        "    render_dashboard()\n"
        "else:\n"
        "    selected_screen = render_navigation(available_screens)\n"
        "    render_screen(selected_screen)"
    )

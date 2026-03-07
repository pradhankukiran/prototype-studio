from __future__ import annotations

import ast
import operator


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
    if isinstance(node, ast.Constant | ast.Name):
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
            raise RuleExpressionError(
                "Only basic helper functions are allowed in rule expressions."
            )
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
        return (
            _evaluate_node(node.body, context)
            if _evaluate_node(node.test, context)
            else _evaluate_node(node.orelse, context)
        )
    raise RuleExpressionError("Unsupported construct in rule expression.")

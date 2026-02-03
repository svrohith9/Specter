from __future__ import annotations

import ast
from typing import Any


class SafeEval(ast.NodeVisitor):
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Num,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.FloorDiv,
    )

    def visit(self, node: ast.AST) -> Any:  # noqa: ANN401
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"Unsupported expression: {type(node).__name__}")
        return super().visit(node)


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Num):
        return float(node.n)
    if isinstance(node, ast.UnaryOp):
        val = _eval(node.operand)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return val
    if isinstance(node, ast.BinOp):
        left = _eval(node.left)
        right = _eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
    raise ValueError("Invalid expression")


async def calculate(expression: str) -> dict[str, Any]:
    try:
        tree = ast.parse(expression, mode="eval")
        SafeEval().visit(tree)
        value = _eval(tree)
        return {"success": True, "data": value, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "data": None, "error": str(exc)}

import ast
import operator as op

description = "Evaluate math expressions safely and optionally round the result."
args = {
    "expression": {"type": "string", "description": "Math expression, e.g. (12*4)+3^2"},
    "round_to": {"type": "integer", "description": "Optional decimal places for rounding"},
}
required = ["expression"]

OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Unsupported expression")


def main(expression, round_to=None):
    try:
        expr = (expression or "").replace("^", "**").strip()
        if not expr:
            return {"error": "expression is required"}

        tree = ast.parse(expr, mode="eval")
        value = _eval(tree.body)

        if round_to is not None:
            value = round(float(value), int(round_to))

        return {"expression": expression, "result": value}
    except Exception as e:
        return {"error": f"calculator tool failed: {e}"}

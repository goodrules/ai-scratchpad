"""Tool use (function calling) with a manual agentic loop and a local, safe calculator tool."""

from __future__ import annotations

import ast
import operator

from _common import DEFAULT, console, default_metadata, get_client, print_header, print_response, tracer

PROMPT = (
    "You have a `calculator` tool. Use it to compute the monthly payment on a "
    "$28,500 car loan at 6.9% annual interest over 60 months using the standard "
    "amortization formula P*r/(1-(1+r)**-n), where r is the monthly rate. Then "
    "state the result rounded to the nearest cent."
)

TOOLS = [
    {
        "name": "calculator",
        "description": (
            "Evaluate a single arithmetic expression and return the numeric result. Supports "
            "+ - * / ** % and parentheses on decimal numbers, e.g. '(28500*0.00575)/(1-(1.00575)**-60)'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate.",
                }
            },
            "required": ["expression"],
        },
    }
]

# A tiny safe evaluator: numbers and arithmetic operators only -- no names, calls, or attribute
# access -- so untrusted model-supplied expressions can't execute arbitrary code.
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(expr: str) -> float:
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](ev(node.operand))
        raise ValueError(f"unsupported expression element: {type(node).__name__}")

    return ev(ast.parse(expr, mode="eval").body)


def calculator(expression: str) -> str:
    try:
        return str(_safe_eval(expression))
    except Exception as e:  # return errors to the model so it can correct itself
        return f"error: {e}"


def run() -> None:
    print_header(f"tools ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    messages = [{"role": "user", "content": PROMPT}]

    # Manual agentic loop: call the model, execute any tool_use blocks it emits, feed the results
    # back, and repeat until it stops requesting tools (capped to avoid an unbounded loop).
    response = None
    for _ in range(6):
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.messages.create(
                model=DEFAULT,
                max_tokens=2048,
                tools=TOOLS,
                messages=messages,
                metadata=default_metadata(),
            )

        tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            break

        # Echo the assistant turn (including tool_use blocks), then return one tool_result per call.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for tu in tool_uses:
            expression = (tu.input or {}).get("expression", "")
            result = calculator(expression)
            console.print(f"[dim]calculator({expression!r}) -> {result}[/dim]")
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result})
        messages.append({"role": "user", "content": results})

    print_response("answer", response)


if __name__ == "__main__":
    run()

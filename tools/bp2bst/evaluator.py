"""Variable resolution and expression evaluation for Android.bp ASTs.

Resolves variable references, evaluates + concatenation for lists and strings,
and applies architecture-specific selections.
"""

from typing import Dict, Optional
from . import ast


class EvalError(Exception):
    pass


class Evaluator:
    """Evaluates Blueprint AST expressions given a variable scope."""

    def __init__(self, variables: Optional[Dict[str, ast.Expression]] = None):
        self.variables: Dict[str, ast.Expression] = dict(variables or {})

    def add_file_variables(self, file: ast.File):
        """Register all top-level assignments from a file."""
        for defn in file.defs:
            if isinstance(defn, ast.Assignment):
                if defn.assigner == "+=":
                    existing = self.variables.get(defn.name)
                    if existing is not None:
                        self.variables[defn.name] = ast.OperatorExpr(
                            left=existing, op="+", right=defn.value
                        )
                    else:
                        self.variables[defn.name] = defn.value
                else:
                    self.variables[defn.name] = defn.value

    def evaluate(self, expr: ast.Expression) -> ast.Expression:
        """Recursively evaluate an expression to a concrete value."""
        if isinstance(expr, (ast.StringExpr, ast.BoolExpr, ast.IntExpr)):
            return expr

        if isinstance(expr, ast.VariableRef):
            if expr.name not in self.variables:
                raise EvalError(f"Undefined variable: {expr.name}")
            return self.evaluate(self.variables[expr.name])

        if isinstance(expr, ast.OperatorExpr):
            left = self.evaluate(expr.left)
            right = self.evaluate(expr.right)

            if expr.op == "+":
                if isinstance(left, ast.ListExpr) and isinstance(right, ast.ListExpr):
                    return ast.ListExpr(values=left.values + right.values)
                if isinstance(left, ast.StringExpr) and isinstance(right, ast.StringExpr):
                    return ast.StringExpr(value=left.value + right.value)
                # If types don't match, return as-is for later handling
                return ast.OperatorExpr(left=left, op=expr.op, right=right)

            return ast.OperatorExpr(left=left, op=expr.op, right=right)

        if isinstance(expr, ast.ListExpr):
            return ast.ListExpr(values=[self.evaluate(v) for v in expr.values])

        if isinstance(expr, ast.MapExpr):
            return ast.MapExpr(
                properties=[
                    ast.Property(name=p.name, value=self.evaluate(p.value))
                    for p in expr.properties
                ]
            )

        if isinstance(expr, ast.SelectExpr):
            # For now, return the select expression as-is (can be resolved
            # later with target configuration)
            return expr

        return expr

    def evaluate_module(self, module: ast.Module) -> ast.Module:
        """Evaluate all property values in a module."""
        return ast.Module(
            type=module.type,
            properties=[
                ast.Property(name=p.name, value=self.evaluate(p.value))
                for p in module.properties
            ],
        )


def extract_string(expr: ast.Expression) -> Optional[str]:
    """Extract a string value from an expression, or None."""
    if isinstance(expr, ast.StringExpr):
        return expr.value
    return None


def extract_string_list(expr: ast.Expression) -> list:
    """Extract a list of strings from a list expression."""
    if isinstance(expr, ast.ListExpr):
        result = []
        for v in expr.values:
            s = extract_string(v)
            if s is not None:
                result.append(s)
        return result
    return []


def extract_bool(expr: ast.Expression) -> Optional[bool]:
    """Extract a boolean value from an expression, or None."""
    if isinstance(expr, ast.BoolExpr):
        return expr.value
    return None


def extract_map(expr: ast.Expression) -> Optional[ast.MapExpr]:
    """Extract a map expression, or None."""
    if isinstance(expr, ast.MapExpr):
        return expr
    return None

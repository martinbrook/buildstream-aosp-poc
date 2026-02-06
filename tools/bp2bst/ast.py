"""AST node types for Android.bp Blueprint files.

Mirrors the Go AST in build/blueprint/parser/ast.go, simplified for Python.
"""

from dataclasses import dataclass, field
from typing import Union


# --- Expression nodes ---

@dataclass
class StringExpr:
    value: str

    def __repr__(self):
        return f"StringExpr({self.value!r})"


@dataclass
class BoolExpr:
    value: bool

    def __repr__(self):
        return f"BoolExpr({self.value})"


@dataclass
class IntExpr:
    value: int

    def __repr__(self):
        return f"IntExpr({self.value})"


@dataclass
class ListExpr:
    values: list = field(default_factory=list)

    def __repr__(self):
        return f"ListExpr({self.values})"


@dataclass
class MapExpr:
    properties: list = field(default_factory=list)  # list of Property

    def __repr__(self):
        return f"MapExpr({self.properties})"

    def get(self, name):
        """Get property value by name, or None."""
        for prop in self.properties:
            if prop.name == name:
                return prop.value
        return None


@dataclass
class VariableRef:
    name: str

    def __repr__(self):
        return f"VariableRef({self.name})"


@dataclass
class OperatorExpr:
    left: "Expression"
    op: str  # "+"
    right: "Expression"

    def __repr__(self):
        return f"OperatorExpr({self.left} {self.op} {self.right})"


@dataclass
class SelectExpr:
    """select(condition_func("arg1", "arg2"), { ... }) expression."""
    func_name: str
    func_args: list  # list of strings
    cases: list = field(default_factory=list)  # list of (patterns, value) tuples

    def __repr__(self):
        return f"SelectExpr({self.func_name}({self.func_args}), {len(self.cases)} cases)"


# Union type for all expressions
Expression = Union[
    StringExpr, BoolExpr, IntExpr, ListExpr, MapExpr,
    VariableRef, OperatorExpr, SelectExpr,
]


# --- Top-level nodes ---

@dataclass
class Property:
    name: str
    value: Expression

    def __repr__(self):
        return f"Property({self.name}: {self.value})"


@dataclass
class Assignment:
    name: str
    value: Expression
    assigner: str = "="  # "=" or "+="

    def __repr__(self):
        return f"Assignment({self.name} {self.assigner} {self.value})"


@dataclass
class Module:
    type: str
    properties: list = field(default_factory=list)  # list of Property

    def __repr__(self):
        return f"Module({self.type}, name={self.name!r})"

    @property
    def name(self):
        for prop in self.properties:
            if prop.name == "name":
                if isinstance(prop.value, StringExpr):
                    return prop.value.value
        return None

    def get(self, name):
        """Get property value by name, or None."""
        for prop in self.properties:
            if prop.name == name:
                return prop.value
        return None


@dataclass
class File:
    name: str
    defs: list = field(default_factory=list)  # list of Assignment | Module

    @property
    def modules(self):
        return [d for d in self.defs if isinstance(d, Module)]

    @property
    def assignments(self):
        return [d for d in self.defs if isinstance(d, Assignment)]

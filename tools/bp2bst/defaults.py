"""cc_defaults inheritance resolution for Android.bp modules.

In Soong, modules can reference `defaults: ["name1", "name2"]` to inherit
properties. This module resolves those chains, merging properties with the
correct precedence: later defaults override earlier ones, and module-level
properties override all defaults.
"""

from typing import Dict, List, Optional
from . import ast
from .evaluator import extract_string_list


class DefaultsResolver:
    """Resolves cc_defaults inheritance chains."""

    def __init__(self):
        # name -> Module for all cc_defaults modules
        self.defaults_registry: Dict[str, ast.Module] = {}

    def register_defaults(self, modules: List[ast.Module]):
        """Register all cc_defaults modules from a parsed file."""
        for module in modules:
            if module.type == "cc_defaults":
                name = module.name
                if name:
                    self.defaults_registry[name] = module

    def resolve(self, module: ast.Module) -> ast.Module:
        """Resolve defaults for a module, returning a new module with merged properties."""
        defaults_prop = module.get("defaults")
        if defaults_prop is None:
            return module

        defaults_names = extract_string_list(defaults_prop)
        if not defaults_names:
            return module

        # Collect all defaults in order, resolving nested defaults
        all_defaults = []
        visited = set()
        for name in defaults_names:
            self._collect_defaults(name, all_defaults, visited)

        # Merge: start with first defaults, overlay subsequent, then overlay module
        merged_props = {}
        for defaults_module in all_defaults:
            self._merge_properties(merged_props, defaults_module.properties)

        # Module properties override defaults (except "defaults" itself)
        self._merge_properties(
            merged_props,
            [p for p in module.properties if p.name != "defaults"],
        )

        # Reconstruct properties list, ensuring "name" is preserved from original
        final_props = [ast.Property(name=k, value=v) for k, v in merged_props.items()]

        # Re-add the "name" property from the original module if it was stripped
        has_name = any(p.name == "name" for p in final_props)
        if not has_name:
            name_prop = module.get("name")
            if name_prop is not None:
                final_props.insert(0, ast.Property(name="name", value=name_prop))

        return ast.Module(type=module.type, properties=final_props)

    def _collect_defaults(self, name: str, result: list, visited: set):
        """Recursively collect defaults, handling chained defaults."""
        if name in visited:
            return
        visited.add(name)

        defaults_module = self.defaults_registry.get(name)
        if defaults_module is None:
            # Unknown defaults — skip silently (may be defined elsewhere)
            return

        # First resolve any nested defaults
        nested_defaults_prop = defaults_module.get("defaults")
        if nested_defaults_prop is not None:
            nested_names = extract_string_list(nested_defaults_prop)
            for nested_name in nested_names:
                self._collect_defaults(nested_name, result, visited)

        result.append(defaults_module)

    def _merge_properties(self, target: dict, properties: list):
        """Merge properties into target dict.

        - Lists are concatenated
        - Maps are recursively merged
        - Scalars are overridden
        """
        for prop in properties:
            name = prop.name
            if name in ("name", "defaults"):
                continue

            if name in target:
                existing = target[name]
                target[name] = self._merge_values(existing, prop.value)
            else:
                target[name] = prop.value

    def _merge_values(self, base: ast.Expression, overlay: ast.Expression) -> ast.Expression:
        """Merge two values according to Soong rules."""
        # List + List = concatenation
        if isinstance(base, ast.ListExpr) and isinstance(overlay, ast.ListExpr):
            return ast.ListExpr(values=base.values + overlay.values)

        # Map + Map = recursive merge
        if isinstance(base, ast.MapExpr) and isinstance(overlay, ast.MapExpr):
            merged = {p.name: p.value for p in base.properties}
            for prop in overlay.properties:
                if prop.name in merged:
                    merged[prop.name] = self._merge_values(merged[prop.name], prop.value)
                else:
                    merged[prop.name] = prop.value
            return ast.MapExpr(
                properties=[ast.Property(name=k, value=v) for k, v in merged.items()]
            )

        # Scalar: overlay wins
        return overlay

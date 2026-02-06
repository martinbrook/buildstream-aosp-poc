"""AST to .bst YAML generator.

Orchestrates parsing, evaluation, defaults resolution, and module conversion
to produce BuildStream element files.
"""

import os
import sys
from typing import Dict, List, Optional, Any

import yaml

from .parser import parse_file, parse_string
from .evaluator import Evaluator
from .defaults import DefaultsResolver
from .module_types import get_handler, supported_types
from . import ast


class ConversionResult:
    """Result of converting an Android.bp file."""

    def __init__(self):
        self.elements: List[Dict[str, Any]] = []  # list of {filename, content}
        self.skipped: List[str] = []  # module names/types that were skipped
        self.errors: List[str] = []  # conversion errors
        self.unsupported: List[str] = []  # unsupported module types


class Converter:
    """Converts Android.bp files to BuildStream .bst elements."""

    def __init__(self, target_arch: str = "x86_64", aosp_root: str = ""):
        self.target_arch = target_arch
        self.aosp_root = aosp_root
        self.defaults_resolver = DefaultsResolver()
        self.evaluator = Evaluator()

    def convert_file(self, bp_path: str, output_prefix: str = "") -> ConversionResult:
        """Convert a single Android.bp file.

        Args:
            bp_path: Path to the Android.bp file
            output_prefix: Prefix for output element filenames (e.g. "external/bzip2/")

        Returns:
            ConversionResult with generated elements and diagnostics
        """
        result = ConversionResult()

        try:
            file_ast = parse_file(bp_path)
        except Exception as e:
            result.errors.append(f"Parse error in {bp_path}: {e}")
            return result

        # Register file-level variables
        self.evaluator.add_file_variables(file_ast)

        # Evaluate all modules
        evaluated_modules = []
        for module in file_ast.modules:
            try:
                evaluated = self.evaluator.evaluate_module(module)
                evaluated_modules.append(evaluated)
            except Exception as e:
                result.errors.append(f"Evaluation error for {module.type} '{module.name}': {e}")

        # Register cc_defaults for resolution
        self.defaults_resolver.register_defaults(evaluated_modules)

        # Determine source directory relative to AOSP root
        source_dir = os.path.dirname(os.path.abspath(bp_path))

        # Convert each module
        for module in evaluated_modules:
            handler = get_handler(module.type)

            if handler is None:
                result.unsupported.append(f"{module.type} '{module.name or '?'}'")
                continue

            # Resolve defaults before conversion
            resolved = self.defaults_resolver.resolve(module)

            try:
                element = handler.convert(
                    resolved,
                    target_arch=self.target_arch,
                    source_dir=source_dir,
                )
            except Exception as e:
                result.errors.append(
                    f"Conversion error for {module.type} '{module.name}': {e}"
                )
                continue

            if element is None:
                result.skipped.append(f"{module.type} '{module.name or '?'}'")
                continue

            # Prefix the filename
            if output_prefix:
                element["filename"] = os.path.join(output_prefix, element["filename"])

            result.elements.append(element)

        return result

    def write_elements(self, result: ConversionResult, output_dir: str):
        """Write generated elements to disk as .bst YAML files."""
        for element in result.elements:
            filepath = os.path.join(output_dir, element["filename"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Custom YAML formatting for readability
            content = self._format_bst(element["content"])

            with open(filepath, "w") as f:
                f.write(content)

    def _format_bst(self, element_dict: dict) -> str:
        """Format a .bst element dict as YAML with a header comment."""
        lines = []

        # Kind
        lines.append(f"kind: {element_dict['kind']}")
        lines.append("")

        # Dependencies
        if "depends" in element_dict:
            lines.append("depends:")
            for dep in element_dict["depends"]:
                lines.append(f"- {dep}")
            lines.append("")

        # Sources
        if "sources" in element_dict and element_dict["sources"]:
            lines.append("sources:")
            for src in element_dict["sources"]:
                lines.append(f"- kind: {src['kind']}")
                lines.append(f"  path: {src['path']}")
            lines.append("")

        # Variables
        if "variables" in element_dict:
            lines.append("variables:")
            for key, value in element_dict["variables"].items():
                if "\n" in str(value):
                    lines.append(f"  {key}: |")
                    for vline in str(value).split("\n"):
                        lines.append(f"    {vline}")
                else:
                    # Quote values that contain special YAML characters
                    if isinstance(value, str) and any(c in value for c in "{}[]#&*!|>',@%"):
                        lines.append(f'  {key}: "{value}"')
                    else:
                        lines.append(f"  {key}: {value}")
            lines.append("")

        # Config (for import elements)
        if "config" in element_dict:
            lines.append("config:")
            for key, value in element_dict["config"].items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        return "\n".join(lines)

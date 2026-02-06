"""Per-module-type handler registry mapping Soong module types to .bst elements.

Each handler knows how to extract properties from a parsed Module AST node
and produce a dictionary suitable for YAML serialization as a .bst element.
"""

from typing import Dict, List, Optional, Any
from . import ast
from .evaluator import extract_string, extract_string_list, extract_bool, extract_map


class ModuleHandler:
    """Base class for module type handlers."""

    # The Soong module type(s) this handler covers
    MODULE_TYPES: List[str] = []

    def can_handle(self, module_type: str) -> bool:
        return module_type in self.MODULE_TYPES

    def convert(self, module: ast.Module, target_arch: str = "x86_64",
                source_dir: str = "") -> Optional[Dict[str, Any]]:
        """Convert a Module AST to a .bst element dict.

        Returns None if the module should be skipped.
        Returns a dict with keys: filename, content (the YAML dict).
        """
        raise NotImplementedError


class CcLibraryStaticHandler(ModuleHandler):
    MODULE_TYPES = ["cc_library_static"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        name = module.name
        if not name:
            return None

        srcs = self._get_srcs(module, target_arch)
        cflags = self._get_cflags(module, target_arch)
        include_dirs = self._get_include_dirs(module)
        export_include_dirs = self._get_export_include_dirs(module)

        element = {
            "kind": "aosp_cc",
            "depends": ["base/aosp-sdk.bst"],
            "sources": [{"kind": "local_external", "path": source_dir}] if source_dir else [],
            "variables": {
                "build-type": "static",
                "lib-name": name,
                "src-files": " ".join(srcs),
            },
        }

        if cflags:
            element["variables"]["extra-cflags"] = " ".join(cflags)
        if include_dirs or export_include_dirs:
            all_includes = set(include_dirs + export_include_dirs)
            flags = " ".join(f"-I{d}" for d in sorted(all_includes))
            element["variables"]["include-flags"] = flags

        # Add static_libs and shared_libs as dependencies
        deps = self._get_lib_deps(module)
        if deps:
            element["depends"].extend(deps)

        filename = f"{name}.bst"
        return {"filename": filename, "content": element}

    def _get_srcs(self, module, target_arch):
        srcs = []
        srcs_prop = module.get("srcs")
        if srcs_prop:
            srcs.extend(extract_string_list(srcs_prop))

        # Check arch-specific srcs
        arch_prop = module.get("arch")
        if arch_prop and isinstance(arch_prop, ast.MapExpr):
            arch_map = extract_map(arch_prop)
            if arch_map:
                arch_specific = arch_map.get(target_arch)
                if arch_specific and isinstance(arch_specific, ast.MapExpr):
                    arch_srcs = arch_specific.get("srcs")
                    if arch_srcs:
                        srcs.extend(extract_string_list(arch_srcs))
        return srcs

    def _get_cflags(self, module, target_arch):
        cflags = []
        cflags_prop = module.get("cflags")
        if cflags_prop:
            cflags.extend(extract_string_list(cflags_prop))

        # Check arch-specific cflags
        arch_prop = module.get("arch")
        if arch_prop and isinstance(arch_prop, ast.MapExpr):
            arch_map = extract_map(arch_prop)
            if arch_map:
                arch_specific = arch_map.get(target_arch)
                if arch_specific and isinstance(arch_specific, ast.MapExpr):
                    arch_cflags = arch_specific.get("cflags")
                    if arch_cflags:
                        cflags.extend(extract_string_list(arch_cflags))
        return cflags

    def _get_include_dirs(self, module):
        result = []
        prop = module.get("local_include_dirs")
        if prop:
            result.extend(extract_string_list(prop))
        prop = module.get("include_dirs")
        if prop:
            result.extend(extract_string_list(prop))
        return result

    def _get_export_include_dirs(self, module):
        prop = module.get("export_include_dirs")
        if prop:
            return extract_string_list(prop)
        return []

    def _get_lib_deps(self, module):
        deps = []
        for dep_type in ("static_libs", "shared_libs", "whole_static_libs",
                         "header_libs"):
            prop = module.get(dep_type)
            if prop:
                lib_names = extract_string_list(prop)
                # Convert library names to .bst element references
                # The actual path depends on where the dependency element lives
                for lib_name in lib_names:
                    deps.append(f"external/{lib_name}.bst")
        return deps


class CcLibrarySharedHandler(CcLibraryStaticHandler):
    MODULE_TYPES = ["cc_library_shared"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        result = super().convert(module, target_arch, source_dir)
        if result:
            result["content"]["variables"]["build-type"] = "shared"
        return result


class CcLibraryHandler(CcLibraryStaticHandler):
    """Handles cc_library which produces both static and shared variants.
    For simplicity, we generate a shared library by default."""
    MODULE_TYPES = ["cc_library"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        result = super().convert(module, target_arch, source_dir)
        if result:
            # cc_library defaults to shared output
            result["content"]["variables"]["build-type"] = "shared"
        return result


class CcBinaryHandler(CcLibraryStaticHandler):
    MODULE_TYPES = ["cc_binary", "cc_binary_host"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        name = module.name
        if not name:
            return None

        srcs = self._get_srcs(module, target_arch)
        cflags = self._get_cflags(module, target_arch)
        include_dirs = self._get_include_dirs(module)
        export_include_dirs = self._get_export_include_dirs(module)

        element = {
            "kind": "aosp_cc",
            "depends": ["base/aosp-sdk.bst"],
            "sources": [{"kind": "local_external", "path": source_dir}] if source_dir else [],
            "variables": {
                "build-type": "binary",
                "binary-name": name,
                "src-files": " ".join(srcs),
            },
        }

        if cflags:
            element["variables"]["extra-cflags"] = " ".join(cflags)
        if include_dirs or export_include_dirs:
            all_includes = set(include_dirs + export_include_dirs)
            flags = " ".join(f"-I{d}" for d in sorted(all_includes))
            element["variables"]["include-flags"] = flags

        deps = self._get_lib_deps(module)
        if deps:
            element["depends"].extend(deps)

        return {"filename": f"{name}.bst", "content": element}


class CcDefaultsHandler(ModuleHandler):
    """cc_defaults are not converted to elements — they're handled by DefaultsResolver."""
    MODULE_TYPES = ["cc_defaults"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        return None  # Skip — defaults are merged into consuming modules


class PrebuiltEtcHandler(ModuleHandler):
    MODULE_TYPES = ["prebuilt_etc", "prebuilt_etc_host"]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        name = module.name
        if not name:
            return None

        src_prop = module.get("src")
        if not src_prop:
            return None

        src = extract_string(src_prop)
        if not src:
            return None

        element = {
            "kind": "import",
            "sources": [{"kind": "local_external", "path": source_dir}] if source_dir else [],
            "config": {"source": src, "target": "/etc"},
        }

        return {"filename": f"{name}.bst", "content": element}


class SkippedHandler(ModuleHandler):
    """Handler for module types we deliberately skip."""
    MODULE_TYPES = [
        "package", "license", "ndk_headers", "ndk_library",
        "cc_test", "cc_test_host", "cc_fuzz", "cc_benchmark",
        "genrule", "filegroup",
        "vndk_prebuilt_shared",
    ]

    def convert(self, module, target_arch="x86_64", source_dir=""):
        return None


# Registry of all handlers
_HANDLERS: List[ModuleHandler] = [
    CcLibraryStaticHandler(),
    CcLibrarySharedHandler(),
    CcLibraryHandler(),
    CcBinaryHandler(),
    CcDefaultsHandler(),
    PrebuiltEtcHandler(),
    SkippedHandler(),
]


def get_handler(module_type: str) -> Optional[ModuleHandler]:
    """Look up the handler for a given module type."""
    for handler in _HANDLERS:
        if handler.can_handle(module_type):
            return handler
    return None


def supported_types() -> List[str]:
    """Return list of all supported module types."""
    types = []
    for handler in _HANDLERS:
        types.extend(handler.MODULE_TYPES)
    return types

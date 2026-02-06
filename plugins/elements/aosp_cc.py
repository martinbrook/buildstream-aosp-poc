"""AOSP C/C++ build element plugin for BuildStream.

Handles cc_library_static, cc_library_shared, and cc_binary module types
using AOSP's prebuilt Clang toolchain. Supports srcs, cflags, include_dirs,
shared_libs, static_libs, and export_include_dirs as YAML configuration keys.

The heavy lifting is done by command templates in aosp_cc.yaml; this class
extends BuildElement with minimal overrides.
"""

from buildstream import BuildElement


class AospCcElement(BuildElement):

    BST_MIN_VERSION = "2.0"


def setup():
    return AospCcElement

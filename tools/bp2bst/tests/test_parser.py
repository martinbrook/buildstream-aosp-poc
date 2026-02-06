"""Tests for the Android.bp parser."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bp2bst.parser import parse_string, parse_file, ParseError
from bp2bst import ast


class TestParserBasics(unittest.TestCase):

    def test_empty_file(self):
        f = parse_string("")
        self.assertEqual(len(f.defs), 0)

    def test_comments_only(self):
        f = parse_string("// this is a comment\n/* block comment */\n")
        self.assertEqual(len(f.defs), 0)

    def test_variable_assignment(self):
        f = parse_string('my_var = ["a", "b"]')
        self.assertEqual(len(f.defs), 1)
        self.assertIsInstance(f.defs[0], ast.Assignment)
        self.assertEqual(f.defs[0].name, "my_var")
        self.assertIsInstance(f.defs[0].value, ast.ListExpr)
        self.assertEqual(len(f.defs[0].value.values), 2)

    def test_variable_plus_assign(self):
        f = parse_string('my_var = ["a"]\nmy_var += ["b"]')
        self.assertEqual(len(f.defs), 2)
        self.assertEqual(f.defs[1].assigner, "+=")

    def test_string_concat(self):
        f = parse_string('x = "hello" + " world"')
        self.assertIsInstance(f.defs[0].value, ast.OperatorExpr)
        self.assertEqual(f.defs[0].value.op, "+")

    def test_list_concat(self):
        f = parse_string('x = ["a"] + ["b"]')
        self.assertIsInstance(f.defs[0].value, ast.OperatorExpr)


class TestParserModules(unittest.TestCase):

    def test_simple_module(self):
        f = parse_string('''
            cc_library_static {
                name: "libbz",
                srcs: ["a.c", "b.c"],
            }
        ''')
        self.assertEqual(len(f.modules), 1)
        m = f.modules[0]
        self.assertEqual(m.type, "cc_library_static")
        self.assertEqual(m.name, "libbz")

    def test_nested_map(self):
        f = parse_string('''
            cc_library {
                name: "test",
                arch: {
                    arm: {
                        cflags: ["-marm"],
                    },
                    x86_64: {
                        cflags: ["-msse2"],
                    },
                },
            }
        ''')
        m = f.modules[0]
        arch = m.get("arch")
        self.assertIsInstance(arch, ast.MapExpr)
        self.assertIsNotNone(arch.get("arm"))

    def test_bool_properties(self):
        f = parse_string('''
            cc_library {
                name: "test",
                host_supported: true,
                enabled: false,
            }
        ''')
        m = f.modules[0]
        self.assertIsInstance(m.get("host_supported"), ast.BoolExpr)
        self.assertTrue(m.get("host_supported").value)
        self.assertFalse(m.get("enabled").value)

    def test_multiple_modules(self):
        f = parse_string('''
            package {
                default_applicable_licenses: ["lic"],
            }
            cc_library_static {
                name: "foo",
                srcs: ["a.c"],
            }
            cc_binary {
                name: "bar",
                srcs: ["main.c"],
            }
        ''')
        self.assertEqual(len(f.modules), 3)
        self.assertEqual(f.modules[0].type, "package")
        self.assertEqual(f.modules[1].type, "cc_library_static")
        self.assertEqual(f.modules[2].type, "cc_binary")

    def test_variable_ref_in_property(self):
        f = parse_string('''
            my_srcs = ["a.c", "b.c"]
            cc_library {
                name: "test",
                srcs: my_srcs,
            }
        ''')
        m = f.modules[0]
        srcs = m.get("srcs")
        self.assertIsInstance(srcs, ast.VariableRef)
        self.assertEqual(srcs.name, "my_srcs")

    def test_list_concat_in_property(self):
        f = parse_string('''
            base_flags = ["-Wall"]
            cc_library {
                name: "test",
                cflags: base_flags + ["-Werror"],
            }
        ''')
        m = f.modules[0]
        cflags = m.get("cflags")
        self.assertIsInstance(cflags, ast.OperatorExpr)


class TestParserRealFiles(unittest.TestCase):
    """Tests against real Android.bp files (if available)."""

    AOSP_ROOT = "/home/vgrade/AAOS-RE/aosp"

    def _skip_if_no_aosp(self):
        if not os.path.isdir(self.AOSP_ROOT):
            self.skipTest("AOSP tree not available")

    def test_bzip2(self):
        self._skip_if_no_aosp()
        f = parse_file(os.path.join(self.AOSP_ROOT, "external/bzip2/Android.bp"))
        module_types = [m.type for m in f.modules]
        self.assertIn("cc_library_static", module_types)
        self.assertIn("cc_binary", module_types)

    def test_zlib(self):
        self._skip_if_no_aosp()
        f = parse_file(os.path.join(self.AOSP_ROOT, "external/zlib/Android.bp"))
        # zlib uses variables and cc_defaults
        self.assertTrue(len(f.assignments) > 0, "zlib should have variable assignments")
        module_names = [m.name for m in f.modules if m.name]
        self.assertIn("libz", module_names)

    def test_expat(self):
        self._skip_if_no_aosp()
        f = parse_file(os.path.join(self.AOSP_ROOT, "external/expat/Android.bp"))
        module_names = [m.name for m in f.modules if m.name]
        self.assertIn("libexpat", module_names)

    def test_libpng(self):
        self._skip_if_no_aosp()
        f = parse_file(os.path.join(self.AOSP_ROOT, "external/libpng/Android.bp"))
        module_names = [m.name for m in f.modules if m.name]
        self.assertIn("libpng", module_names)


if __name__ == "__main__":
    unittest.main()

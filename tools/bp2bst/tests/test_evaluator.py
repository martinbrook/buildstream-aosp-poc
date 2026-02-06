"""Tests for the evaluator and defaults resolver."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bp2bst.parser import parse_string
from bp2bst.evaluator import Evaluator, extract_string, extract_string_list
from bp2bst.defaults import DefaultsResolver
from bp2bst import ast


class TestEvaluator(unittest.TestCase):

    def test_resolve_variable(self):
        f = parse_string('my_flags = ["-Wall", "-Werror"]')
        ev = Evaluator()
        ev.add_file_variables(f)
        result = ev.evaluate(ast.VariableRef(name="my_flags"))
        self.assertIsInstance(result, ast.ListExpr)
        self.assertEqual(len(result.values), 2)

    def test_list_concat(self):
        f = parse_string('a = ["x"]\nb = a + ["y"]')
        ev = Evaluator()
        ev.add_file_variables(f)
        result = ev.evaluate(ast.VariableRef(name="b"))
        self.assertIsInstance(result, ast.ListExpr)
        strings = extract_string_list(result)
        self.assertEqual(strings, ["x", "y"])

    def test_plus_assign(self):
        f = parse_string('a = ["x"]\na += ["y"]')
        ev = Evaluator()
        ev.add_file_variables(f)
        result = ev.evaluate(ast.VariableRef(name="a"))
        strings = extract_string_list(result)
        self.assertEqual(strings, ["x", "y"])

    def test_chained_variable_refs(self):
        f = parse_string('''
            base = ["-O2"]
            extended = base + ["-Wall"]
        ''')
        ev = Evaluator()
        ev.add_file_variables(f)
        result = ev.evaluate(ast.VariableRef(name="extended"))
        strings = extract_string_list(result)
        self.assertEqual(strings, ["-O2", "-Wall"])


class TestDefaultsResolver(unittest.TestCase):

    def test_simple_defaults(self):
        f = parse_string('''
            cc_defaults {
                name: "my_defaults",
                cflags: ["-Wall"],
                srcs: ["a.c"],
            }
            cc_library {
                name: "mylib",
                defaults: ["my_defaults"],
                srcs: ["b.c"],
            }
        ''')
        ev = Evaluator()
        ev.add_file_variables(f)
        modules = [ev.evaluate_module(m) for m in f.modules]

        dr = DefaultsResolver()
        dr.register_defaults(modules)

        mylib = modules[1]
        resolved = dr.resolve(mylib)

        self.assertEqual(resolved.name, "mylib")
        cflags = extract_string_list(resolved.get("cflags"))
        self.assertEqual(cflags, ["-Wall"])

        # srcs should be concatenated: defaults + module
        srcs = extract_string_list(resolved.get("srcs"))
        self.assertEqual(srcs, ["a.c", "b.c"])

    def test_chained_defaults(self):
        f = parse_string('''
            cc_defaults {
                name: "base_defaults",
                cflags: ["-O2"],
            }
            cc_defaults {
                name: "extra_defaults",
                defaults: ["base_defaults"],
                cflags: ["-Wall"],
            }
            cc_library {
                name: "mylib",
                defaults: ["extra_defaults"],
            }
        ''')
        ev = Evaluator()
        ev.add_file_variables(f)
        modules = [ev.evaluate_module(m) for m in f.modules]

        dr = DefaultsResolver()
        dr.register_defaults(modules)

        mylib = modules[2]
        resolved = dr.resolve(mylib)

        cflags = extract_string_list(resolved.get("cflags"))
        # base_defaults then extra_defaults -> concat
        self.assertEqual(cflags, ["-O2", "-Wall"])

    def test_map_merge(self):
        f = parse_string('''
            cc_defaults {
                name: "my_defaults",
                arch: {
                    arm: {
                        cflags: ["-marm"],
                    },
                },
            }
            cc_library {
                name: "mylib",
                defaults: ["my_defaults"],
                arch: {
                    x86: {
                        cflags: ["-msse"],
                    },
                },
            }
        ''')
        ev = Evaluator()
        ev.add_file_variables(f)
        modules = [ev.evaluate_module(m) for m in f.modules]

        dr = DefaultsResolver()
        dr.register_defaults(modules)

        mylib = modules[1]
        resolved = dr.resolve(mylib)

        arch = resolved.get("arch")
        self.assertIsNotNone(arch)
        # Should have both arm and x86
        arm = arch.get("arm")
        x86 = arch.get("x86")
        self.assertIsNotNone(arm, "arm arch should be present from defaults")
        self.assertIsNotNone(x86, "x86 arch should be present from module")


class TestDefaultsResolverRealFiles(unittest.TestCase):
    """Tests against real Android.bp files."""

    AOSP_ROOT = "/home/vgrade/AAOS-RE/aosp"

    def _skip_if_no_aosp(self):
        if not os.path.isdir(self.AOSP_ROOT):
            self.skipTest("AOSP tree not available")

    def test_zlib_defaults_resolution(self):
        """Test that zlib's cc_defaults chain resolves correctly."""
        self._skip_if_no_aosp()
        from bp2bst.parser import parse_file

        f = parse_file(os.path.join(self.AOSP_ROOT, "external/zlib/Android.bp"))
        ev = Evaluator()
        ev.add_file_variables(f)
        modules = [ev.evaluate_module(m) for m in f.modules]

        dr = DefaultsResolver()
        dr.register_defaults(modules)

        # Find libz_static
        libz_static = None
        for m in modules:
            if m.name == "libz_static":
                libz_static = dr.resolve(m)
                break
        self.assertIsNotNone(libz_static)
        self.assertEqual(libz_static.name, "libz_static")

        srcs = extract_string_list(libz_static.get("srcs"))
        self.assertIn("adler32.c", srcs)
        self.assertIn("deflate.c", srcs)

        cflags = extract_string_list(libz_static.get("cflags"))
        self.assertIn("-DHAVE_HIDDEN", cflags)


if __name__ == "__main__":
    unittest.main()

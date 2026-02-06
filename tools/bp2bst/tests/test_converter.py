"""Tests for the full converter pipeline."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bp2bst.converter import Converter


class TestConverterRealFiles(unittest.TestCase):
    """Integration tests against real Android.bp files."""

    AOSP_ROOT = "/home/vgrade/AAOS-RE/aosp"

    def _skip_if_no_aosp(self):
        if not os.path.isdir(self.AOSP_ROOT):
            self.skipTest("AOSP tree not available")

    def test_bzip2_conversion(self):
        self._skip_if_no_aosp()
        converter = Converter(target_arch="x86_64")
        bp_path = os.path.join(self.AOSP_ROOT, "external/bzip2/Android.bp")
        result = converter.convert_file(bp_path, output_prefix="external/bzip2")

        self.assertEqual(len(result.errors), 0, f"Errors: {result.errors}")
        self.assertEqual(len(result.unsupported), 0, f"Unsupported: {result.unsupported}")
        self.assertEqual(len(result.elements), 2)

        filenames = [e["filename"] for e in result.elements]
        self.assertIn("external/bzip2/libbz.bst", filenames)
        self.assertIn("external/bzip2/bzip2.bst", filenames)

        # Check libbz element
        libbz = [e for e in result.elements if "libbz" in e["filename"]][0]
        self.assertEqual(libbz["content"]["kind"], "aosp_cc")
        self.assertEqual(libbz["content"]["variables"]["build-type"], "static")
        self.assertIn("blocksort.c", libbz["content"]["variables"]["src-files"])

    def test_expat_conversion(self):
        self._skip_if_no_aosp()
        converter = Converter(target_arch="x86_64")
        bp_path = os.path.join(self.AOSP_ROOT, "external/expat/Android.bp")
        result = converter.convert_file(bp_path, output_prefix="external/expat")

        self.assertEqual(len(result.errors), 0, f"Errors: {result.errors}")
        self.assertEqual(len(result.elements), 1)
        self.assertIn("external/expat/libexpat.bst", result.elements[0]["filename"])

    def test_zlib_conversion(self):
        self._skip_if_no_aosp()
        converter = Converter(target_arch="x86_64")
        bp_path = os.path.join(self.AOSP_ROOT, "external/zlib/Android.bp")
        result = converter.convert_file(bp_path, output_prefix="external/zlib")

        self.assertEqual(len(result.errors), 0, f"Errors: {result.errors}")
        # Should have at least libz, libz_static, libz_stable, zlib_bench
        self.assertGreaterEqual(len(result.elements), 4)

        filenames = [e["filename"] for e in result.elements]
        self.assertIn("external/zlib/libz.bst", filenames)
        self.assertIn("external/zlib/libz_static.bst", filenames)

    def test_libpng_conversion(self):
        self._skip_if_no_aosp()
        converter = Converter(target_arch="x86_64")
        bp_path = os.path.join(self.AOSP_ROOT, "external/libpng/Android.bp")
        result = converter.convert_file(bp_path, output_prefix="external/libpng")

        self.assertEqual(len(result.errors), 0, f"Errors: {result.errors}")
        filenames = [e["filename"] for e in result.elements]
        self.assertIn("external/libpng/libpng.bst", filenames)

        # libpng should depend on libz
        libpng = [e for e in result.elements if "libpng.bst" in e["filename"]][0]
        deps = libpng["content"]["depends"]
        self.assertTrue(any("libz" in d for d in deps), "libpng should depend on libz")


if __name__ == "__main__":
    unittest.main()

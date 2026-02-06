#!/usr/bin/env python3
"""CLI for bp2bst: Android.bp to BuildStream converter.

Usage:
    bp2bst convert <path/to/Android.bp> [--target-arch x86_64] [--output-dir elements/]
    bp2bst parse <path/to/Android.bp>   (dump AST for debugging)
    bp2bst info <path/to/Android.bp>    (show module summary)
"""

import argparse
import json
import os
import sys

# Add parent directory to path so we can import bp2bst
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bp2bst.parser import parse_file
from bp2bst.converter import Converter
from bp2bst.module_types import supported_types


def cmd_convert(args):
    """Convert Android.bp to .bst elements."""
    bp_path = args.file
    if not os.path.exists(bp_path):
        print(f"Error: file not found: {bp_path}", file=sys.stderr)
        return 1

    converter = Converter(
        target_arch=args.target_arch,
        aosp_root=args.aosp_root,
    )

    # Determine output prefix from the bp file path relative to AOSP root
    output_prefix = args.prefix
    if not output_prefix and args.aosp_root:
        bp_dir = os.path.dirname(os.path.abspath(bp_path))
        aosp_abs = os.path.abspath(args.aosp_root)
        if bp_dir.startswith(aosp_abs):
            output_prefix = os.path.relpath(bp_dir, aosp_abs)

    result = converter.convert_file(bp_path, output_prefix=output_prefix)

    if result.errors:
        print("Errors:", file=sys.stderr)
        for err in result.errors:
            print(f"  {err}", file=sys.stderr)

    if result.unsupported:
        print(f"Unsupported module types ({len(result.unsupported)}):", file=sys.stderr)
        for u in result.unsupported:
            print(f"  {u}", file=sys.stderr)

    if result.skipped:
        print(f"Skipped ({len(result.skipped)}):", file=sys.stderr)
        for s in result.skipped:
            print(f"  {s}", file=sys.stderr)

    if not result.elements:
        print("No elements generated.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Would generate {len(result.elements)} element(s):")
        for elem in result.elements:
            print(f"  {elem['filename']}")
            print(converter._format_bst(elem["content"]))
            print("---")
    else:
        output_dir = args.output_dir
        converter.write_elements(result, output_dir)
        print(f"Generated {len(result.elements)} element(s) in {output_dir}/:")
        for elem in result.elements:
            print(f"  {elem['filename']}")

    return 0


def cmd_parse(args):
    """Parse and dump AST for debugging."""
    bp_path = args.file
    if not os.path.exists(bp_path):
        print(f"Error: file not found: {bp_path}", file=sys.stderr)
        return 1

    file_ast = parse_file(bp_path)

    print(f"File: {file_ast.name}")
    print(f"Definitions: {len(file_ast.defs)}")
    print()

    for defn in file_ast.defs:
        print(f"  {defn}")


def cmd_info(args):
    """Show module summary."""
    bp_path = args.file
    if not os.path.exists(bp_path):
        print(f"Error: file not found: {bp_path}", file=sys.stderr)
        return 1

    file_ast = parse_file(bp_path)

    print(f"File: {bp_path}")
    print(f"Variables: {len(file_ast.assignments)}")
    print(f"Modules: {len(file_ast.modules)}")
    print()

    for module in file_ast.modules:
        name = module.name or "<unnamed>"
        props = [p.name for p in module.properties]
        print(f"  {module.type} '{name}'")
        print(f"    properties: {', '.join(props)}")


def main():
    parser = argparse.ArgumentParser(
        description="bp2bst: Android.bp to BuildStream .bst converter"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # convert
    p_convert = subparsers.add_parser("convert", help="Convert Android.bp to .bst elements")
    p_convert.add_argument("file", help="Path to Android.bp file")
    p_convert.add_argument("--target-arch", default="x86_64", help="Target architecture (default: x86_64)")
    p_convert.add_argument("--output-dir", default="elements", help="Output directory (default: elements/)")
    p_convert.add_argument("--aosp-root", default="", help="AOSP source tree root")
    p_convert.add_argument("--prefix", default="", help="Output filename prefix")
    p_convert.add_argument("--dry-run", "-n", action="store_true", help="Print elements without writing files")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse Android.bp and dump AST")
    p_parse.add_argument("file", help="Path to Android.bp file")

    # info
    p_info = subparsers.add_parser("info", help="Show module summary")
    p_info.add_argument("file", help="Path to Android.bp file")

    args = parser.parse_args()

    if args.command == "convert":
        return cmd_convert(args)
    elif args.command == "parse":
        return cmd_parse(args)
    elif args.command == "info":
        return cmd_info(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)

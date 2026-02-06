# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A proof-of-concept evaluating **BuildStream 2.6.0** for building C++ projects in sandboxed environments, with investigation into Buildbarn integration for remote execution. Conclusion: BuildStream and Buildbarn use incompatible protocols (Remote Asset API vs REAPI), making direct integration impractical without middleware like BuildGrid.

## Build Commands

All commands require the virtualenv activated first: `source .venv/bin/activate`

```bash
# Helper script (handles venv activation automatically)
./run-poc.sh build          # Build hello.bst
./run-poc.sh run            # Build, checkout, run in Alpine container
./run-poc.sh clean          # Clean build cache
./run-poc.sh shell          # Interactive sandbox shell

# Direct BuildStream commands
bst show hello.bst          # Show pipeline status
bst build hello.bst         # Build single element
bst build greet-app.bst     # Build with dependencies (base-sdk -> libgreet -> greet-app)
bst artifact checkout hello.bst --directory /tmp/output
```

## Architecture

### BuildStream Concepts

- **project.conf** - Root config: project name, element path, plugin registration (`make`, `cmake`, `autotools` from `buildstream-plugins` pip package), sandbox settings (runs as root uid/gid 0)
- **Elements** (`elements/*.bst`) - YAML build definitions specifying kind, dependencies, sources, and build/install commands
- **Sources** (`sources/`) - Local source trees referenced by elements

### Element Dependency Graph

```
base-sdk.bst (Alpine sysroot via import)
├── hello.bst (standalone C++ binary)
├── libgreet.bst (shared library, .so + header)
└── greet-app.bst (links against libgreet.bst)
```

### Key Details

- **Sysroot**: `sources/sysroot/` contains an extracted Alpine Linux 3.19 rootfs with `build-base` (GCC 13.2.1, musl libc, make). This is imported as `base-sdk.bst` and provides the complete sandbox filesystem.
- **Sandbox**: Builds run in bubblewrap isolation. The sandbox has no access to the host system - all tools must come from the sysroot.
- **Elements use `kind: manual`** with explicit `g++` compile and `install` commands (not Makefiles, despite Makefiles existing in source dirs).
- **Artifacts cached** at `~/.cache/buildstream/`.
- **Running built binaries** requires Docker with Alpine to provide matching musl libc runtime: `docker run --rm -v /tmp/output:/app alpine:3.19 /app/usr/bin/hello`

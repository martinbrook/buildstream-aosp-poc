# BuildStream AOSP Proof of Concept

Converting the Android 15 (AAOS) build system from Soong to [BuildStream 2.6.0](https://docs.buildstream.build/), with [Buildbarn](https://github.com/buildbarn) for remote execution via REAPI v2.

## What This PoC Demonstrates

1. **AOSP Clang toolchain** running inside BuildStream's bubblewrap sandbox
2. **Android.bp to .bst converter** (`bp2bst`) — recursive descent parser achieving 99.8% parse success on 1000 AOSP files
3. **Real AOSP module builds** — bzip2, expat, zlib, libpng, libffi, lz4, pcre converted and building with AOSP Clang r522817
4. **Buildbarn compatibility** — BuildStream's `SandboxBuildBoxRun` constructs standard REAPI v2 `Action` protobufs, directly compatible with Buildbarn for remote execution
5. **Custom BuildStream plugins** — `aosp_cc` element plugin and `local_external` source plugin

## Architecture

### AOSP Toolchain in Sandbox

```
BuildStream sandbox (bubblewrap)
├── /bin/sh                          ← Alpine base-sdk (busybox)
├── /lib/x86_64-linux-gnu/           ← Host glibc (for clang-18)
│   ├── ld-linux-x86-64.so.2
│   ├── libc.so.6, libm.so.6, ...
├── /aosp/prebuilts/
│   ├── clang/host/linux-x86/clang-r522817/  ← AOSP Clang
│   ├── build-tools/
│   │   ├── linux-x86/bin/           ← make, ninja, bison, flex
│   │   └── sysroots/x86_64-unknown-linux-musl/  ← musl sysroot
│   └── jdk/jdk17/linux-x86/        ← JDK 17 (future)
└── /buildstream-install/            ← Build output
```

Key discovery: AOSP's `clang` binary is a Go wrapper that shells out to `clang.real` → `clang-18`. The Go wrapper fails in the sandbox, so we call `clang-18` directly with `--driver-mode=g++` for C++.

### Remote Execution with Buildbarn

```
BuildStream (bst build)
  → buildbox-casd        → [gRPC REAPI v2] → Buildbarn (:8980)
  → buildbox-run-bubblewrap                    ├── bb-storage (CAS + AC)
                                               ├── bb-scheduler
                                               └── bb-worker / bb-runner
```

BuildStream's sandbox internally constructs standard REAPI v2 `Action` protobufs — the same protocol Buildbarn implements. The only protocol mismatch is for *artifact caching* (BuildStream uses Remote Asset API), not remote execution.

### Element Dependency Graph

```
base-sdk.bst (Alpine — provides /bin/sh)
toolchains/host-glibc.bst (glibc for clang-18)
toolchains/clang-r522817.bst (AOSP Clang)
toolchains/bionic-sysroot.bst (musl sysroot)
toolchains/build-tools.bst (make, ninja, etc.)
    └── base/aosp-sdk.bst (stack combining all above)
            ├── external/bzip2/libbz.bst (static library)
            │   └── external/bzip2/bzip2.bst (binary)
            ├── external/zlib/libz.bst
            │   └── external/libpng/libpng.bst
            ├── external/expat/libexpat.bst
            └── ...
```

## Project Structure

```
buildstream-poc/
├── project.conf                    # BuildStream config, plugin registration
├── plugins/
│   ├── elements/
│   │   ├── aosp_cc.py              # C/C++ build element plugin
│   │   └── aosp_cc.yaml            # Command templates (compile/link/install)
│   └── sources/
│       └── local_external.py       # Source plugin for absolute paths
├── elements/
│   ├── base-sdk.bst                # Alpine Linux sysroot
│   ├── base/aosp-sdk.bst           # AOSP toolchain stack
│   ├── toolchains/
│   │   ├── clang-r522817.bst       # AOSP Clang r522817
│   │   ├── bionic-sysroot.bst      # musl sysroot
│   │   ├── build-tools.bst         # make, ninja, bison, flex
│   │   ├── host-glibc.bst          # Host glibc for clang-18
│   │   └── jdk17.bst               # JDK 17 (for future Java phases)
│   ├── external/                   # Converted AOSP modules
│   │   ├── bzip2/                  # libbz.bst, bzip2.bst
│   │   ├── expat/                  # libexpat.bst
│   │   ├── zlib/                   # libz.bst + 4 variants
│   │   ├── libpng/                 # libpng.bst, libpng_ndk.bst
│   │   ├── libffi/                 # libffi.bst
│   │   ├── lz4/                    # liblz4.bst
│   │   └── pcre/                   # libpcre2.bst
│   ├── hello.bst                   # Simple C++ test (Alpine GCC)
│   ├── libgreet.bst                # Shared library example
│   └── greet-app.bst               # App linking to libgreet
├── tools/bp2bst/                   # Android.bp → .bst converter
│   ├── parser.py                   # Recursive descent Blueprint parser
│   ├── ast.py                      # AST node types
│   ├── evaluator.py                # Variable resolution
│   ├── defaults.py                 # cc_defaults inheritance
│   ├── converter.py                # AST → .bst YAML generation
│   ├── module_types.py             # Per-type handler registry
│   ├── cli.py                      # CLI interface
│   └── tests/                      # 28 tests (parser, evaluator, converter)
└── sources/                        # Local source trees
    ├── hello/, libgreet/, greet-app/
    ├── sysroot/                    # Alpine rootfs (gitignored, 224MB)
    └── host-glibc/                 # glibc libs (gitignored)
```

## Quick Start

### Prerequisites

- Python 3.11+
- BuildStream 2.6.0 (`pip install buildstream`)
- AOSP source tree at `/home/vgrade/AAOS-RE/aosp` (for toolchain elements)
- bubblewrap (`apt install bubblewrap`)

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install buildstream buildstream-plugins pyyaml pytest
```

### Building AOSP Modules

```bash
source .venv/bin/activate

# Build bzip2 static library with AOSP Clang
bst build external/bzip2/libbz.bst

# Build bzip2 binary (depends on libbz)
bst build external/bzip2/bzip2.bst

# Checkout and verify
bst artifact checkout external/bzip2/bzip2.bst --directory /tmp/bzip2-output
file /tmp/bzip2-output/usr/bin/bzip2
# Output: ELF 64-bit LSB executable, x86-64, statically linked
```

### Using the bp2bst Converter

```bash
source .venv/bin/activate

# Convert an Android.bp file to BuildStream elements
python3 -m tools.bp2bst.cli convert \
    /path/to/aosp/external/bzip2/Android.bp \
    --prefix external/bzip2 \
    --output-dir elements/

# Parse and dump AST (for debugging)
python3 -m tools.bp2bst.cli parse /path/to/Android.bp

# Show module summary
python3 -m tools.bp2bst.cli info /path/to/Android.bp
```

### Running Tests

```bash
source .venv/bin/activate
pytest tools/bp2bst/tests/ -v
# 28 tests covering parser, evaluator, defaults resolution, and end-to-end conversion
```

### Building Alpine Examples

```bash
./run-poc.sh build          # Build hello.bst with Alpine GCC
./run-poc.sh run            # Build, checkout, run in container

# Multi-element dependency chain
bst build greet-app.bst
bst artifact checkout greet-app.bst --directory /tmp/greet-output
docker run --rm -v /tmp/greet-output:/app alpine:3.19 \
    sh -c "export LD_LIBRARY_PATH=/app/usr/lib && /app/usr/bin/greet-app World"
```

## bp2bst Converter

The `tools/bp2bst/` converter parses Android.bp (Blueprint) files and generates BuildStream `.bst` element definitions.

### Supported Module Types

| Blueprint Type | BuildStream Mapping | Status |
|---|---|---|
| `cc_library_static` | `aosp_cc` (build-type: static) | Working |
| `cc_library_shared` | `aosp_cc` (build-type: shared) | Working |
| `cc_library` | Generates both static + shared | Working |
| `cc_binary` | `aosp_cc` (build-type: binary) | Working |
| `cc_defaults` | Resolved during conversion | Working |
| `prebuilt_etc` | `import` | Working |

### Parser Capabilities

- Module definitions, variable assignments (`=`, `+=`)
- String/list concatenation (`+` operator)
- Nested maps (`arch: { arm: { ... } }`)
- `select()` expressions
- `//` and `/* */` comments
- Booleans, integers, variable references
- `cc_defaults` chained inheritance (5+ levels)

### Known Limitations

- Cross-module dependency paths need manual fixup (converter generates `external/{lib}.bst` but actual path may be `external/{subdir}/{lib}.bst`)
- `filegroup(...)` function call syntax not supported (1 failure in 1000 files)
- Architecture-specific properties (`arch: { x86_64: { ... } }`) parsed but not yet applied during conversion

## Custom Plugins

### `aosp_cc` Element Plugin

Handles C/C++ compilation using AOSP Clang. Configured via variables:

```yaml
kind: aosp_cc
variables:
  build-type: static|shared|binary
  lang: c|c++
  src-files: "file1.c file2.c"
  lib-name: libfoo          # for static/shared
  binary-name: foo           # for binary
  extra-cflags: "-Wall"
  extra-ldflags: "-lz"
  include-flags: "-I."
```

### `local_external` Source Plugin

References absolute paths outside the project directory — necessary because BuildStream's built-in `local` source rejects symlinks and paths outside the project root.

```yaml
sources:
- kind: local_external
  path: /home/user/aosp/external/bzip2
```

## Key Technical Findings

### Buildbarn Integration

- **Remote execution**: BuildStream's `SandboxBuildBoxRun` extends `SandboxREAPI` and constructs standard REAPI v2 `Action` protobufs — directly compatible with Buildbarn
- **Artifact caching**: Protocol mismatch — BuildStream uses Remote Asset API (`build.bazel.remote.asset.v1.Fetch`), Buildbarn uses REAPI ActionCache. Bridgeable via BuildGrid middleware
- **Conclusion**: Buildbarn integration for remote execution is viable without middleware; only artifact caching needs bridging

### AOSP Clang in Sandbox

- AOSP's `clang` is a Go wrapper → fails in sandbox → call `clang-18` directly
- `clang-18` is dynamically linked against glibc → need host glibc in sandbox (`host-glibc.bst`)
- For static linking with musl sysroot: `--rtlib=compiler-rt -unwindlib=none` (musl has no libgcc)

## Roadmap

- [x] Phase 0: Toolchain import — AOSP Clang building C code in sandbox
- [x] Phase 1: Android.bp parser + basic C/C++ conversion (7 modules)
- [ ] Phase 2: Cross-compilation + architecture variants (50+ modules)
- [ ] Phase 3: Buildbox remote execution with Buildbarn
- [ ] Phase 4: Java/Android plugins (`java_library`, `android_app`)
- [ ] Phase 5: Rust, AIDL, Protobuf module types
- [ ] Phase 6: Full system integration (partition images, APEX)

## References

- [BuildStream Documentation](https://docs.buildstream.build/)
- [BuildStream Remote Execution](https://docs.buildstream.build/master/using_configuring_remote_execution.html)
- [Buildbarn](https://github.com/buildbarn)
- [REAPI Proto](https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto)
- [Android Blueprint Format](https://source.android.com/docs/setup/reference/androidbp)
- [BuildGrid](https://buildgrid.build/) (for artifact cache bridging)
- [buildbox-common](https://gitlab.com/BuildGrid/buildbox/buildbox-common)

# BuildStream + Buildbarn Proof of Concept

## Summary

This PoC demonstrates BuildStream 2.6.0 building C++ projects using an Alpine Linux sysroot. Builds execute locally in a bubblewrap sandbox with dependency tracking and caching.

## What This PoC Demonstrates

1. **Local BuildStream builds** with bubblewrap sandboxing
2. **Dependency management** - libgreet.bst must build before greet-app.bst
3. **Artifact caching** - subsequent builds use cached artifacts
4. **Custom sysroots** - Alpine Linux with build-base tools

## Key Findings

### BuildStream + Buildbarn Integration Challenges

1. **Protocol Mismatch for Artifact Caching**

   BuildStream uses the **Remote Asset API** (`build.bazel.remote.asset.v1.Fetch`) for artifact caching, while Buildbarn implements the standard **REAPI** services:
   - `build.bazel.remote.execution.v2.ActionCache`
   - `build.bazel.remote.execution.v2.ContentAddressableStorage`
   - `build.bazel.remote.execution.v2.Execution`

   These are different protocols. BuildStream cannot use Buildbarn's CAS/AC as an artifact cache.

2. **Remote Execution Requires buildbox Tools**

   BuildStream's remote execution uses **buildbox** tools:
   - `buildbox-casd` - CAS daemon
   - `buildbox-run-bubblewrap` - sandbox runner
   - `buildbox-worker` - worker process

   These are not packaged in Debian/Ubuntu and must be built from source:
   https://gitlab.com/BuildGrid/buildbox/buildbox-common

3. **Sysroot Requirements**

   BuildStream builds in fully isolated sandboxes. Unlike Bazel (which can use the host system), BuildStream requires a complete root filesystem (sysroot) with all build tools.

### What Works

- Local BuildStream builds with bubblewrap sandboxing
- Custom sysroots (Docker images exported to filesystem)
- Artifact caching to local disk
- Dependency resolution and build ordering

### What Doesn't Work (Without Additional Infrastructure)

- Using Buildbarn as a remote artifact cache (protocol mismatch)
- Remote execution on Buildbarn workers (needs buildbox tools)
- Direct integration without middleware

## Project Structure

```
buildstream-poc/
├── project.conf              # BuildStream configuration
├── run-poc.sh               # Helper script
├── elements/
│   ├── base-sdk.bst         # Alpine Linux sysroot
│   ├── hello.bst            # Simple C++ hello world
│   ├── libgreet.bst         # Shared library example
│   └── greet-app.bst        # App linking to libgreet
└── sources/
    ├── hello/               # Simple C++ source
    ├── libgreet/            # Shared library source
    ├── greet-app/           # Application source
    └── sysroot/             # Extracted Alpine rootfs
```

## Quick Start

```bash
# Use the helper script
./run-poc.sh build         # Build hello.bst
./run-poc.sh run           # Build, checkout, and run in container
./run-poc.sh clean         # Clean build cache

# Or use BuildStream directly
source .venv/bin/activate
bst show hello.bst         # Show pipeline status
bst build hello.bst        # Build
bst artifact checkout hello.bst --directory /tmp/output
```

## Building the Multi-Element Example

```bash
source .venv/bin/activate

# Show dependency chain
bst show greet-app.bst
# Output shows: base-sdk -> libgreet -> greet-app

# Build (automatically builds dependencies in order)
bst build greet-app.bst

# Checkout and run
bst artifact checkout greet-app.bst --directory /tmp/greet-output
docker run --rm -v /tmp/greet-output:/app alpine:3.19 \
    sh -c "export LD_LIBRARY_PATH=/app/usr/lib && /app/usr/bin/greet-app World"
# Output: Hello, World! Welcome to BuildStream.
```

## Alternative Approaches

### Option 1: BuildGrid as Middleware

BuildGrid (https://buildgrid.build/) can bridge BuildStream and Buildbarn:
- Implements Remote Asset API (for BuildStream)
- Can proxy to Buildbarn for execution
- Adds complexity but enables integration

### Option 2: Use Buildbarn for AOSP Only

Keep BuildStream and AOSP builds separate:
- AOSP uses reproxy + Buildbarn (current setup)
- BuildStream uses its own local/remote caching

### Option 3: Custom Asset API Implementation

Implement `build.bazel.remote.asset.v1` service in Buildbarn. This would require:
- Understanding Asset API semantics
- Mapping to Buildbarn's existing storage
- Contributing upstream or maintaining a fork

## Conclusion

BuildStream is a capable meta-build system with strong dependency management and reproducibility features. However, integrating it with Buildbarn for AOSP builds would require:

1. Protocol bridging (BuildStream ↔ REAPI)
2. buildbox tools deployment
3. Sysroot matching AOSP toolchains

**Recommendation**: For AAOS/AOSP builds, continue with the current **Soong + reproxy + Buildbarn** architecture. BuildStream's benefits don't outweigh the integration complexity for Android-specific builds.

## Buildbarn Services (for reference)

Your Buildbarn cluster at `localhost:8980` provides:
```
build.bazel.remote.execution.v2.ActionCache
build.bazel.remote.execution.v2.Capabilities
build.bazel.remote.execution.v2.ContentAddressableStorage
build.bazel.remote.execution.v2.Execution
google.bytestream.ByteStream
grpc.health.v1.Health
```

BuildStream expects: `build.bazel.remote.asset.v1.Fetch` (not provided)

## References

- [BuildStream Documentation](https://docs.buildstream.build/)
- [BuildStream 2.x Remote Execution](https://docs.buildstream.build/master/using_configuring_remote_execution.html)
- [BuildGrid](https://buildgrid.build/)
- [buildbox-common](https://gitlab.com/BuildGrid/buildbox/buildbox-common)
- [Remote Asset API Proto](https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/asset/v1/remote_asset.proto)
- [REAPI Proto](https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto)

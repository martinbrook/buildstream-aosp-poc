# Host glibc runtime libraries import
# Provides /lib64/ld-linux-x86-64.so.2 and glibc shared libs needed by
# AOSP's prebuilt clang-18 (which is dynamically linked against glibc).
# This is a PoC workaround; for production, clang would be statically linked.

kind: import

sources:
- kind: local
  path: sources/host-glibc

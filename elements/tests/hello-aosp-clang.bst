# Test element: compile C++ with AOSP Clang toolchain
# Validates that the AOSP Clang toolchain is accessible in the sandbox

kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local
  path: sources/test-aosp-clang

variables:
  build-type: binary
  binary-name: hello
  src-files: hello.cpp
  extra-cflags: "-O2 -Wall"

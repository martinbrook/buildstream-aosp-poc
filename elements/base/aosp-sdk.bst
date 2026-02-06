# AOSP SDK stack element
# Combines all toolchain imports into a single dependency.
# Elements that need the full AOSP build environment depend on this.
# Includes base-sdk (Alpine sysroot) for shell utilities (sh, install, sed, etc.)

kind: stack

depends:
- base-sdk.bst
- toolchains/host-glibc.bst
- toolchains/clang-r522817.bst
- toolchains/bionic-sysroot.bst
- toolchains/build-tools.bst

# AOSP Clang r522817 toolchain import
# Imports the prebuilt Clang compiler, mounted at the AOSP path layout
# so build commands using absolute AOSP paths work unchanged.

kind: import

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/prebuilts/clang/host/linux-x86/clang-r522817

config:
  target: /aosp/prebuilts/clang/host/linux-x86/clang-r522817

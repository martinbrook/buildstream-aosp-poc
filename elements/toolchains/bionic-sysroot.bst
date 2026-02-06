# AOSP build-tools musl sysroot import
# Provides libc, libm, libdl, crt objects and headers for x86_64 host builds.

kind: import

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/prebuilts/build-tools/sysroots/x86_64-unknown-linux-musl

config:
  target: /aosp/prebuilts/build-tools/sysroots/x86_64-unknown-linux-musl

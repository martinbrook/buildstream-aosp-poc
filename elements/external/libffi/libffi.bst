kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/libffi

variables:
  build-type: shared
  lib-name: libffi
  src-files: src/closures.c src/debug.c src/java_raw_api.c src/prep_cif.c src/raw_api.c src/types.c src/x86/ffi64.c src/x86/ffiw64.c src/x86/unix64.S src/x86/win64.S
  extra-cflags: -Wall -Werror -Wno-error=incompatible-pointer-types -Wno-incompatible-pointer-types -Wno-deprecated-declarations -Wno-missing-field-initializers -Wno-null-pointer-arithmetic -Wno-pointer-arith -Wno-sign-compare -Wno-unused-parameter -Wno-unused-result
  include-flags: -Iinclude

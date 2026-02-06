kind: aosp_cc

depends:
- base/aosp-sdk.bst
- external/zlib/libz.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/libpng

variables:
  build-type: static
  lib-name: libpng_ndk
  src-files: "*.c intel/*"
  extra-cflags: -std=gnu89 -Wall -Werror -Wno-unused-parameter -ftrapv
  include-flags: -I.

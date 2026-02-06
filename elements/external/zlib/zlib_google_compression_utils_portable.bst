kind: aosp_cc

depends:
- base/aosp-sdk.bst
- external/zlib/libz.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/zlib

variables:
  build-type: shared
  lib-name: zlib_google_compression_utils_portable
  src-files: google/compression_utils_portable.cc
  extra-cflags: -DHAVE_HIDDEN -DZLIB_CONST -DCHROMIUM_ZLIB_NO_CASTAGNOLI -O3 -Wall -Werror -Wno-deprecated-non-prototype -Wno-unused -Wno-unused-parameter -DX86_NOT_WINDOWS -DCPU_NO_SIMD -DINFLATE_CHUNK_READ_64LE
  include-flags: -I. -Igoogle

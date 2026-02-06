kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/zlib

variables:
  build-type: shared
  lib-name: libz_static
  src-files: adler32.c adler32_simd.c compress.c cpu_features.c crc32.c crc32_simd.c crc_folding.c deflate.c gzclose.c gzlib.c gzread.c gzwrite.c infback.c inffast.c inflate.c inftrees.c trees.c uncompr.c zutil.c
  extra-cflags: -DHAVE_HIDDEN -DZLIB_CONST -DCHROMIUM_ZLIB_NO_CASTAGNOLI -O3 -Wall -Werror -Wno-deprecated-non-prototype -Wno-unused -Wno-unused-parameter -DX86_NOT_WINDOWS -DCPU_NO_SIMD -DINFLATE_CHUNK_READ_64LE
  include-flags: -I.

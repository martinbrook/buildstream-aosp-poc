kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/bzip2

variables:
  build-type: static
  lib-name: libbz
  src-files: blocksort.c bzlib.c compress.c crctable.c decompress.c huffman.c randtable.c
  extra-cflags: -O3 -DUSE_MMAP -Werror -Wno-unused-parameter
  include-flags: -I.

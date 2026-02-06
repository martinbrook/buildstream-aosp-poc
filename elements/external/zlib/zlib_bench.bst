kind: aosp_cc

depends:
- base/aosp-sdk.bst
- external/zlib/libz.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/zlib

variables:
  build-type: binary
  binary-name: zlib_bench
  src-files: contrib/bench/zlib_bench.cc
  extra-cflags: -Wall -Werror -Wno-deprecated-non-prototype -Wno-unused-parameter

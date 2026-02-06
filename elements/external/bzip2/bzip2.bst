kind: aosp_cc

depends:
- base/aosp-sdk.bst
- external/bzip2/libbz.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/bzip2

variables:
  build-type: binary
  binary-name: bzip2
  src-files: bzip2.c
  extra-cflags: -Werror -Wno-unused-parameter
  extra-ldflags: "-L/usr/lib -lbz -static --rtlib=compiler-rt -unwindlib=none"

kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/lz4/lib

variables:
  build-type: shared
  lib-name: liblz4
  src-files: lz4.c lz4hc.c lz4frame.c xxhash.c
  extra-cflags: -Wall -Werror
  include-flags: -I.

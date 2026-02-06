kind: aosp_cc

depends:
- base/aosp-sdk.bst

sources:
- kind: local_external
  path: /home/vgrade/AAOS-RE/aosp/external/expat

variables:
  build-type: shared
  lib-name: libexpat
  src-files: expat/lib/xmlparse.c expat/lib/xmlrole.c expat/lib/xmltok.c
  extra-cflags: -fno-strict-aliasing -Wall -Werror -Wmissing-prototypes -Wstrict-prototypes -DHAVE_EXPAT_CONFIG_H -UWIN32_LEAN_AND_MEAN -include stdio.h
  include-flags: -Ilib

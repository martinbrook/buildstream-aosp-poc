# Shared library element demonstrating BuildStream dependency handling

kind: manual

depends:
- base-sdk.bst

sources:
- kind: local
  path: sources/libgreet

config:
  build-commands:
  - g++ -Wall -O2 -fPIC -shared -o libgreet.so greet.cpp

  install-commands:
  - install -D libgreet.so "%{install-root}/usr/lib/libgreet.so"
  - install -D greet.h "%{install-root}/usr/include/greet.h"

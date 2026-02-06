# Application element that depends on libgreet
# Demonstrates BuildStream's dependency resolution

kind: manual

depends:
- base-sdk.bst
- libgreet.bst

sources:
- kind: local
  path: sources/greet-app

config:
  build-commands:
  - g++ -Wall -O2 -I/usr/include -o greet-app main.cpp -L/usr/lib -lgreet -Wl,-rpath,/usr/lib

  install-commands:
  - install -D greet-app "%{install-root}/usr/bin/greet-app"

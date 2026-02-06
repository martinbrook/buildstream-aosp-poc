# Hello World element - demonstrates BuildStream build
# Uses manual element to compile C++ source with explicit commands

kind: manual

depends:
- base-sdk.bst

sources:
- kind: local
  path: sources/hello

config:
  build-commands:
  - g++ -Wall -O2 -o hello hello.cpp

  install-commands:
  - install -D hello "%{install-root}%{bindir}/hello"

variables:
  bindir: /usr/bin

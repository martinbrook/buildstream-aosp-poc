CXX = g++
CXXFLAGS = -Wall -O2
PREFIX ?= /usr

hello: hello.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

install: hello
	install -D hello $(DESTDIR)$(PREFIX)/bin/hello

clean:
	rm -f hello

.PHONY: install clean

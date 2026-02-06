CXX = g++
CXXFLAGS = -Wall -O2
LDFLAGS = -L/usr/lib -lgreet -Wl,-rpath,/usr/lib
PREFIX ?= /usr

greet-app: main.cpp
	$(CXX) $(CXXFLAGS) -I/usr/include -o $@ $< $(LDFLAGS)

install: greet-app
	install -D greet-app $(DESTDIR)$(PREFIX)/bin/greet-app

clean:
	rm -f greet-app

.PHONY: install clean

CXX = g++
CXXFLAGS = -Wall -O2 -fPIC
PREFIX ?= /usr

libgreet.so: greet.cpp greet.h
	$(CXX) $(CXXFLAGS) -shared -o $@ greet.cpp

install: libgreet.so
	install -D libgreet.so $(DESTDIR)$(PREFIX)/lib/libgreet.so
	install -D greet.h $(DESTDIR)$(PREFIX)/include/greet.h

clean:
	rm -f libgreet.so

.PHONY: install clean

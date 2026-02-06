#include "greet.h"

namespace greet {
    std::string get_greeting(const std::string& name) {
        return "Hello, " + name + "! Welcome to BuildStream.";
    }
}

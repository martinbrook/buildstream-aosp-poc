#include <iostream>
#include <greet.h>

int main(int argc, char* argv[]) {
    std::string name = (argc > 1) ? argv[1] : "BuildStream User";
    std::cout << greet::get_greeting(name) << std::endl;
    return 0;
}

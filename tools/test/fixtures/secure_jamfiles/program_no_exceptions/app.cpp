// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names /webcpp/secure//secure alone: it holds a timing guard, compares two
// buffers in constant time and erases one of them.

#include <webcpp/secure.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    namespace secure = webcpp::secure;
    std::array<std::uint8_t, 16> first{};
    std::array<std::uint8_t, 16> second{};
    first.fill(0x5a);
    second.fill(0x5a);
    secure::timing_guard const guard;
    if (secure::constant_time_equal(first, second)) {
        std::printf("equal\n");
    }
    secure::erase_secret(first);
    bool erased = true;
    for (std::uint8_t const byte : first) {
        erased = erased && byte == 0;
    }
    if (erased && !secure::constant_time_equal(first, second)) {
        std::printf("erased\n");
    }
    return 0;
}

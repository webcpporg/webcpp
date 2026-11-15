// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// argon2id on another backend than backends::sodium stops with spec section 3.3's text.

#include <webcpp/hash/argon2.hpp>
#include <webcpp/hash/backends/hash2.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 16> salt{};
    auto done = webcpp::hash::argon2id<webcpp::hash::backends::hash2>(
        output, {}, salt, webcpp::hash::argon2id_interactive);
    return done ? 0 : 1;
}

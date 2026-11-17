// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// blake2b_subkey on another backend than backends::sodium stops with spec section 3.3's text.

#include <webcpp/hash/backends/hash2.hpp>
#include <webcpp/hash/blake2b_subkey.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> subkey{};
    std::array<std::uint8_t, 32> master_key{};
    std::array<std::uint8_t, 8> context{};
    auto done =
        webcpp::hash::blake2b_subkey<webcpp::hash::backends::hash2>(subkey, master_key, 1, context);
    return done ? 0 : 1;
}

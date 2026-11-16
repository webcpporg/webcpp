// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// pbkdf2 on backends::sodium stops with spec section 3.3's text: libsodium has no PBKDF2.

#include <webcpp/hash/pbkdf2.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 64> output{};
    std::array<std::uint8_t, 4> input{};
    auto done = webcpp::hash::pbkdf2<webcpp::hash::hmac_sha2_512, webcpp::hash::backends::sodium>(
        output, input, input, 1);
    return done ? 0 : 1;
}

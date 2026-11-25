// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// scrypt on its default backend, backends::sodium, in a program that does not link libsodium stops
// with the instruction to add /third_party//sodium (spec section 5.7, the third row).

#include <webcpp/hash/scrypt.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 16> salt{};
    auto done = webcpp::hash::scrypt(
        output, {}, salt,
        webcpp::hash::scrypt_parameters{.cost = 1024, .block_size = 8, .parallelism = 1});
    return done ? 0 : 1;
}

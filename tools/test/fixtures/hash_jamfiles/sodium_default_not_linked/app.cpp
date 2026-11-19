// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// mac over a tag whose default is backends::sodium, in a program that does not link libsodium,
// stops with the instruction to add /third_party//sodium (spec 5.7).

#include <webcpp/hash/mac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 32> key{};
    auto done = webcpp::hash::mac<webcpp::hash::macs::blake2b_mac>(output, key, {});
    return done ? 0 : 1;
}

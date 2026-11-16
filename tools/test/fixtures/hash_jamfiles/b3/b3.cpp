// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program over BLAKE3's C implementation: the digests of BLAKE3's official vectors of length 0
// and 1 (test_vectors.json, whose input is the bytes 0, 1, 2, ... modulo 251).

#include <webcpp/hash/blake3.hpp>

#include <cstdint>
#include <cstdio>
#include <span>

namespace {

// Prints label, a space and bytes in lowercase hex, then a newline.
void print_hex(char const* label, std::span<std::uint8_t const> bytes) {
    std::printf("%s ", label);
    for (std::uint8_t const b : bytes) {
        std::printf("%02x", static_cast<unsigned>(b));
    }
    std::printf("\n");
}

}  // namespace

int main() {
    webcpp::hash::blake3 empty;
    print_hex("blake3", empty.result());
    std::uint8_t const zero = 0;
    webcpp::hash::blake3 hasher;
    hasher.update(&zero, 1);
    print_hex("blake3", hasher.result());
    return 0;
}

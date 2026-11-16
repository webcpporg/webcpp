// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program over XKCP: Keccak-256 (Ethereum's, the original padding) of nothing and of "abc".

#include <webcpp/hash/keccak.hpp>

#include <cstdint>
#include <cstdio>
#include <span>
#include <string_view>

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
    webcpp::hash::keccak_256 empty;
    print_hex("keccak_256", empty.result());
    std::string_view const abc = "abc";
    webcpp::hash::keccak_256 hasher;
    hasher.update(abc.data(), abc.size());
    print_hex("keccak_256", hasher.result());
    return 0;
}

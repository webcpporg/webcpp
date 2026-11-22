// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A user's program over backends::botan: Whirlpool of "abc" (its authors' vector), and HMAC over
// Streebog-256 of RFC 7836 section 4.1.1's example, natively and on Emscripten.

#include <webcpp/hash.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <numeric>
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
    namespace hash = webcpp::hash;
    std::array<std::uint8_t, 3> const abc{0x61, 0x62, 0x63};
    std::array<std::uint8_t, 64> digest{};
    if (!hash::digest_of<hash::digests::whirlpool, hash::backends::botan>(digest, abc)) {
        return 1;
    }
    print_hex("whirlpool", digest);
    std::array<std::uint8_t, 32> key{};
    std::iota(key.begin(), key.end(), std::uint8_t{0});
    std::array<std::uint8_t, 16> const message{0x01, 0x26, 0xbd, 0xb8, 0x78, 0x00, 0xaf, 0x21,
                                               0x43, 0x41, 0x45, 0x65, 0x63, 0x78, 0x01, 0x00};
    std::array<std::uint8_t, 32> tag{};
    if (!hash::mac<hash::macs::hmac<hash::digests::streebog_256>, hash::backends::botan>(tag, key,
                                                                                         message)) {
        return 1;
    }
    print_hex("hmac_streebog_256", tag);
    return 0;
}

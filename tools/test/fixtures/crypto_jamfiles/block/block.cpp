// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Encrypts the FIPS-197 appendix C.3 block with AES-256 on ctaes, checks it, and decrypts it again.
#include <webcpp/crypto/backends/ctaes.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

int main() {
    std::array<std::uint8_t, 32> key{};
    for (std::size_t i = 0; i < key.size(); ++i) {
        key[i] = static_cast<std::uint8_t>(i);
    }
    std::array<std::uint8_t, 16> const plain{
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
    };
    std::array<std::uint8_t, 16> const expected{
        0x8e, 0xa2, 0xb7, 0xca, 0x51, 0x67, 0x45, 0xbf,
        0xea, 0xfc, 0x49, 0x90, 0x4b, 0x49, 0x60, 0x89,
    };
    std::array<std::uint8_t, 16> block = plain;
    auto aes = webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::ctaes>::make(key);
    bool const ok =
        aes && aes->encrypt(block) && block == expected && aes->decrypt(block) && block == plain;
    std::printf("ctaes aes256 %s\n", ok ? "ok" : "FAILED");
    return ok ? 0 : 1;
}

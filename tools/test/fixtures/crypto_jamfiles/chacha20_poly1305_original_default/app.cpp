// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals libsodium's own case of the original ChaCha20-Poly1305 (its 8-byte nonce,
// test/default/aead_chacha20poly1305.exp) on the default backend, checks the tag and the
// ciphertext against libsodium's, opens it again, and prints the backend that ran. The key and
// nonce are the test's: a real program draws its key from random_device and numbers its nonces.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>
#include <webcpp/crypto/equal.hpp>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <string_view>

int main() {
    using aead = webcpp::crypto::ciphers::chacha20_poly1305_original<>;
    std::array<std::uint8_t, 32> const key{
        0x42, 0x90, 0xbc, 0xb1, 0x54, 0x17, 0x35, 0x31, 0xf3, 0x14, 0xaf,
        0x57, 0xf3, 0xbe, 0x3b, 0x50, 0x06, 0xda, 0x37, 0x1e, 0xce, 0x27,
        0x2a, 0xfa, 0x1b, 0x5d, 0xbd, 0xd1, 0x10, 0x0a, 0x10, 0x07,
    };
    std::array<std::uint8_t, 8> const iv{0xcd, 0x7c, 0xf6, 0x7b, 0xe3, 0x9c, 0x79, 0x4a};
    std::array<std::uint8_t, 10> const additional_data{0x87, 0xe2, 0x29, 0xd4, 0x50,
                                                       0x08, 0x45, 0xa0, 0x79, 0xc0};
    std::array<std::uint8_t, 10> const plaintext{0x86, 0xd0, 0x99, 0x74, 0x84,
                                                 0x0b, 0xde, 0xd2, 0xa5, 0xca};
    auto data = plaintext;
    std::array<std::uint8_t, 16> const expected_tag{0x67, 0x7d, 0xab, 0xf4, 0xe3, 0xd2, 0x4b, 0x87,
                                                    0x6b, 0xb2, 0x84, 0x75, 0x38, 0x96, 0xe1, 0xd6};
    std::array<std::uint8_t, 10> const expected_head{0xe3, 0xe4, 0x46, 0xf7, 0xed,
                                                     0xe9, 0xa1, 0x9b, 0x62, 0xa4};
    auto sealer = aead::make(key);
    bool ok = false;
    if (sealer) {
        auto const tag = sealer->seal(iv, additional_data, data);
        ok = tag && webcpp::crypto::equal(*tag, expected_tag) &&
             std::equal(expected_head.begin(), expected_head.end(), data.begin()) &&
             sealer->open(iv, additional_data, data, expected_tag) && data == plaintext;
    }
    auto const name = aead::backend_type::name;
    std::printf("chacha20_poly1305_original %s backend=%.*s\n", ok ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return ok ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals one zero block under AES-256-GCM with the default backend and checks it against the
// GCM specification's test case 14 (key, IV and plaintext all zero), then opens it again, and
// prints the backend that ran. The zero key and IV are the test vector's: a real program draws
// its key from random_device and never reuses an IV under it.
#include <webcpp/crypto/ciphers/aes256_gcm.hpp>
#include <webcpp/crypto/equal.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 12> const iv{};
    std::array<std::uint8_t, 16> data{};
    std::array<std::uint8_t, 16> const cipher{
        0xce, 0xa7, 0x40, 0x3d, 0x4d, 0x60, 0x6b, 0x6e,
        0x07, 0x4e, 0xc5, 0xd3, 0xba, 0xf3, 0x9d, 0x18,
    };
    std::array<std::uint8_t, 16> const expected_tag{
        0xd0, 0xd1, 0xc8, 0xa7, 0x99, 0x99, 0x6b, 0xf0,
        0x26, 0x5b, 0x98, 0xb5, 0xd4, 0x8a, 0xb9, 0x19,
    };
    auto aead = webcpp::crypto::ciphers::aes256_gcm::make(key);
    if (!aead) {
        return 1;
    }
    auto const tag = aead->seal(iv, {}, data);
    bool const sealed = tag && data == cipher && webcpp::crypto::equal(*tag, expected_tag);
    bool const opened =
        aead->open(iv, {}, data, expected_tag) && data == std::array<std::uint8_t, 16>{};
    auto const name = webcpp::crypto::ciphers::aes256_gcm::backend_type::name;
    std::printf("aes256_gcm %s backend=%.*s\n", sealed && opened ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return sealed && opened ? 0 : 1;
}

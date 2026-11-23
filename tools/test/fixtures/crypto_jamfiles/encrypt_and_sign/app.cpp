// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals one zero block under AES-256-GCM with the default backend and checks it against the
// NIST test vector (GCM test case 14), opens it again, then signs a message with BIP340 through
// libsecp256k1, verifies the signature, and refuses a changed message.
#include <webcpp/crypto/ciphers/aes256_gcm.hpp>
#include <webcpp/crypto/constant_time_equal.hpp>
#include <webcpp/crypto/curves/secp256k1.hpp>
#include <webcpp/crypto/signing.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 12> const nonce{};
    std::array<std::uint8_t, 16> data{};
    std::array<std::uint8_t, 16> const cipher{
        0xce, 0xa7, 0x40, 0x3d, 0x4d, 0x60, 0x6b, 0x6e,
        0x07, 0x4e, 0xc5, 0xd3, 0xba, 0xf3, 0x9d, 0x18,
    };
    std::array<std::uint8_t, 16> const expected_tag{
        0xd0, 0xd1, 0xc8, 0xa7, 0x99, 0x99, 0x6b, 0xf0,
        0x26, 0x5b, 0x98, 0xb5, 0xd4, 0x8a, 0xb9, 0x19,
    };
    auto aead = webcpp::crypto::ciphers::aes256_gcm::from_key(key);
    if (!aead) {
        return 1;
    }
    auto const tag = aead->seal(nonce, {}, data);
    bool const sealed =
        tag && data == cipher && webcpp::crypto::constant_time_equal(*tag, expected_tag);
    bool const opened =
        aead->open(nonce, {}, data, expected_tag) && data == std::array<std::uint8_t, 16>{};
    auto const name = webcpp::crypto::ciphers::aes256_gcm::backend_type::name;
    std::printf("aes256_gcm %s backend=%.*s\n", sealed && opened ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());

    namespace secp256k1 = webcpp::crypto::curves::secp256k1;
    std::array<std::uint8_t, 32> secret{};
    secret.fill(0x42);
    std::array<std::uint8_t, 32> message{};
    message.fill(0x17);
    std::array<std::uint8_t, 32> const aux{};
    auto pair = secp256k1::keypair::from_secret(secret);
    bool signed_ok = false;
    if (pair) {
        auto const signature = pair->sign(webcpp::crypto::schnorr, message, aux);
        auto const public_key = pair->public_key();
        signed_ok =
            signature && public_key &&
            webcpp::crypto::verify(webcpp::crypto::schnorr, *signature, message, *public_key);
        message[0] ^= 1U;
        signed_ok = signed_ok && !webcpp::crypto::verify(webcpp::crypto::schnorr, *signature,
                                                         message, *public_key);
    }
    std::printf("schnorr %s\n", signed_ok ? "ok" : "FAILED");
    return sealed && opened && signed_ok ? 0 : 1;
}

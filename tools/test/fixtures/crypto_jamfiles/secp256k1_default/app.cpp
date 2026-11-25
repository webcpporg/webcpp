// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Signs BIP 340's first test vector (secret key 3, a zero message and zero auxiliary data) with
// a key pair on the default backend, checks the signature against the vector's and verifies it,
// and prints the backend that ran. The secret key is the vector's: a real program draws its own.
#include <webcpp/crypto/curves/secp256k1.hpp>
#include <webcpp/crypto/signing.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    namespace secp256k1 = webcpp::crypto::curves::secp256k1;
    std::array<std::uint8_t, 32> secret{};
    secret[31] = 3;
    std::array<std::uint8_t, 32> const message{};
    std::array<std::uint8_t, 32> const aux{};
    std::array<std::uint8_t, 64> const expected{
        0xe9, 0x07, 0x83, 0x1f, 0x80, 0x84, 0x8d, 0x10, 0x69, 0xa5, 0x37, 0x1b, 0x40,
        0x24, 0x10, 0x36, 0x4b, 0xdf, 0x1c, 0x5f, 0x83, 0x07, 0xb0, 0x08, 0x4c, 0x55,
        0xf1, 0xce, 0x2d, 0xca, 0x82, 0x15, 0x25, 0xf6, 0x6a, 0x4a, 0x85, 0xea, 0x8b,
        0x71, 0xe4, 0x82, 0xa7, 0x4f, 0x38, 0x2d, 0x2c, 0xe5, 0xeb, 0xee, 0xe8, 0xfd,
        0xb2, 0x17, 0x2f, 0x47, 0x7d, 0xf4, 0x90, 0x0d, 0x31, 0x05, 0x36, 0xc0,
    };
    auto const key = secp256k1::keypair::from_secret(secret);
    bool ok = false;
    if (key) {
        auto const signature = key->sign(webcpp::crypto::schnorr, message, aux);
        auto const public_key = key->public_key();
        ok = signature && public_key &&
             webcpp::secure::constant_time_equal(signature->bytes(), expected) &&
             webcpp::crypto::verify(webcpp::crypto::schnorr, *signature, message, *public_key);
    }
    auto const name = secp256k1::keypair::backend_type::name;
    std::printf("schnorr %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

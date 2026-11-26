// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Signs RFC 8032's first Ed25519 test (section 7.1, TEST 1: the empty message) with a key pair
// made from its seed on the default backend, checks the signature against the RFC's and verifies
// it, and prints the backend that ran. The seed is the RFC's: a real program draws its own.
#include <webcpp/crypto/curves/ed25519.hpp>
#include <webcpp/crypto/signing.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <span>

int main() {
    namespace crypto = webcpp::crypto;
    namespace secure = webcpp::secure;
    namespace ed25519 = webcpp::crypto::curves::ed25519;
    std::array<std::uint8_t, 32> const seed{
        0x9d, 0x61, 0xb1, 0x9d, 0xef, 0xfd, 0x5a, 0x60, 0xba, 0x84, 0x4a,
        0xf4, 0x92, 0xec, 0x2c, 0xc4, 0x44, 0x49, 0xc5, 0x69, 0x7b, 0x32,
        0x69, 0x19, 0x70, 0x3b, 0xac, 0x03, 0x1c, 0xae, 0x7f, 0x60,
    };
    std::array<std::uint8_t, 64> const expected{
        0xe5, 0x56, 0x43, 0x00, 0xc3, 0x60, 0xac, 0x72, 0x90, 0x86, 0xe2, 0xcc, 0x80,
        0x6e, 0x82, 0x8a, 0x84, 0x87, 0x7f, 0x1e, 0xb8, 0xe5, 0xd9, 0x74, 0xd8, 0x73,
        0xe0, 0x65, 0x22, 0x49, 0x01, 0x55, 0x5f, 0xb8, 0x82, 0x15, 0x90, 0xa3, 0x3b,
        0xac, 0xc6, 0x1e, 0x39, 0x70, 0x1c, 0xf9, 0xb4, 0x6b, 0xd2, 0x5b, 0xf5, 0xf0,
        0x59, 0x5b, 0xbe, 0x24, 0x65, 0x51, 0x41, 0x43, 0x8e, 0x7a, 0x10, 0x0b,
    };
    std::span<std::uint8_t const> const message{};
    auto const key = ed25519::keypair::from_secret(seed);
    bool ok = false;
    if (key) {
        auto const signature = key->sign(crypto::eddsa, message);
        auto const public_key = key->public_key();
        ok = signature && public_key && secure::constant_time_equal(signature->bytes(), expected) &&
             crypto::verify(crypto::eddsa, *signature, message, *public_key).has_value();
    }
    auto const name = ed25519::keypair::backend_type::name;
    std::printf("ed25519 %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

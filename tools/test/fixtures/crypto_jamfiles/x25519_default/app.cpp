// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Agrees RFC 7748's shared secret (section 6.1) from Alice's key pair, made from her secret key,
// and Bob's public key on the default backend, checks it against the RFC's, and prints the
// backend that ran. The keys are the RFC's: a real program draws its own, and never prints a
// shared secret.
#include <webcpp/crypto/constant_time_equal.hpp>
#include <webcpp/crypto/curves/x25519.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    namespace x25519 = webcpp::crypto::curves::x25519;
    std::array<std::uint8_t, 32> const alice_secret{
        0x77, 0x07, 0x6d, 0x0a, 0x73, 0x18, 0xa5, 0x7d, 0x3c, 0x16, 0xc1,
        0x72, 0x51, 0xb2, 0x66, 0x45, 0xdf, 0x4c, 0x2f, 0x87, 0xeb, 0xc0,
        0x99, 0x2a, 0xb1, 0x77, 0xfb, 0xa5, 0x1d, 0xb9, 0x2c, 0x2a,
    };
    std::array<std::uint8_t, 32> const bob_public{
        0xde, 0x9e, 0xdb, 0x7d, 0x7b, 0x7d, 0xc1, 0xb4, 0xd3, 0x5b, 0x61,
        0xc2, 0xec, 0xe4, 0x35, 0x37, 0x3f, 0x83, 0x43, 0xc8, 0x5b, 0x78,
        0x67, 0x4d, 0xad, 0xfc, 0x7e, 0x14, 0x6f, 0x88, 0x2b, 0x4f,
    };
    std::array<std::uint8_t, 32> const expected{
        0x4a, 0x5d, 0x9d, 0x5b, 0xa4, 0xce, 0x2d, 0xe1, 0x72, 0x8e, 0x3b,
        0xf4, 0x80, 0x35, 0x0f, 0x25, 0xe0, 0x7e, 0x21, 0xc9, 0x47, 0xd1,
        0x9e, 0x33, 0x76, 0xf0, 0x9b, 0x3c, 0x1e, 0x16, 0x17, 0x42,
    };
    auto const alice = x25519::keypair::from_secret(alice_secret);
    auto const bob = x25519::public_key::from_bytes(bob_public);
    if (!alice || !bob) {
        std::printf("x25519 FAILED\n");
        return 1;
    }
    auto const shared = alice->agree(*bob);
    bool const ok = shared && webcpp::crypto::constant_time_equal(shared->bytes(), expected);
    auto const name = x25519::keypair::backend_type::name;
    std::printf("x25519 %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

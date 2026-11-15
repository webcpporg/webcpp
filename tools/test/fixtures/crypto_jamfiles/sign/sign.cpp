// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Signs a message with BIP340 through libsecp256k1, verifies it, and refuses a changed one.
#include <webcpp/crypto/secp256k1.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    namespace secp256k1 = webcpp::crypto::secp256k1;
    std::array<std::uint8_t, 32> secret{};
    secret.fill(0x42);
    std::array<std::uint8_t, 32> message{};
    message.fill(0x17);
    std::array<std::uint8_t, 32> const aux{};
    auto key = secp256k1::keypair::make(secret);
    bool ok = false;
    if (key) {
        auto const signature = key->sign_schnorr(message, aux);
        auto const public_key = key->xonly_public_key();
        ok = signature && public_key && secp256k1::verify_schnorr(*signature, message, *public_key);
        message[0] ^= 1;
        ok = ok && !secp256k1::verify_schnorr(*signature, message, *public_key);
    }
    std::printf("schnorr %s\n", ok ? "ok" : "FAILED");
    return ok ? 0 : 1;
}

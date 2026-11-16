// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Makes a key pair and signs once: the program reads libsecp256k1's canary, so that a library
// built other than by webcpp's third_party/Jamfile fails to link.
#include <webcpp/crypto/curves/secp256k1.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> secret{};
    secret.fill(0x42);
    std::array<std::uint8_t, 32> const message{};
    std::array<std::uint8_t, 32> const aux{};
    auto key = webcpp::crypto::curves::secp256k1::keypair::make(secret);
    return key && key->sign_schnorr(message, aux) ? 0 : 1;
}

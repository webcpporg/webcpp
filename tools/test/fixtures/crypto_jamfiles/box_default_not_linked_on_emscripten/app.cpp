// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// As test/messages/box_default_not_linked, on Emscripten.

#include <webcpp/crypto/curves/x25519.hpp>
#include <webcpp/crypto/public_key_encryption/box.hpp>
#include <webcpp/crypto/public_key_encryption/sealed_box.hpp>
#include <webcpp/crypto/secret_key_encryption/secretbox.hpp>

#include <array>
#include <cstdint>

namespace {

namespace crypto = webcpp::crypto;

/**
 * Calls each, the key pair and the peer's public key parameters: making them would call X25519's
 * engine, whose own refusal is not the one under test.
 */
bool called(crypto::curves::x25519::keypair const& own_keypair,
            crypto::curves::x25519::public_key const& peer_public_key) {
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 48> sealed{};
    return crypto::secret_key_encryption::secretbox<>::from_key(key) &&
           crypto::secret_key_encryption::secretbox_xchacha20poly1305<>::from_key(key) &&
           crypto::public_key_encryption::box::from_keys(own_keypair, peer_public_key) &&
           crypto::public_key_encryption::box_xchacha20poly1305::from_keys(own_keypair,
                                                                           peer_public_key) &&
           crypto::public_key_encryption::sealed_box::seal(peer_public_key, {}, sealed);
}

}  // namespace

// The function is compiled, which is the test; it is never run.
int main() {
    static_cast<void>(&called);
    return 0;
}

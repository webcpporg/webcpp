// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that makes an X25519 key pair and agrees a shared secret on its default backend,
// libsodium on every target, without linking it, stops where it calls it, with the line that
// links libsodium, the one backend that has it (design D32).
#include <webcpp/crypto/curves/x25519.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace x25519 = webcpp::crypto::curves::x25519;
    std::array<std::uint8_t, 32> const key{9};
    auto const key_pair = x25519::keypair::from_secret(key);
    auto const peer = x25519::public_key::from_bytes(key);
    return key_pair && peer && key_pair->agree(*peer) ? 0 : 1;
}

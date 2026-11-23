// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals a message to Bob's public key on the default backend, opens it with Bob's key pair,
// checks that it opened as it was sealed, and prints the backend that ran. Bob's secret key is
// fixed here: a real program draws it from random_device.
#include <webcpp/crypto/curves/x25519.hpp>
#include <webcpp/crypto/public_key_encryption/sealed_box.hpp>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <string_view>

int main() {
    using webcpp::crypto::public_key_encryption::sealed_box;
    std::array<std::uint8_t, 32> bob_secret{};
    bob_secret.fill(0x11);
    auto const bob_public = webcpp::crypto::curves::x25519::public_key(bob_secret);
    constexpr std::string_view feedback = "The coffee machine on the third floor is broken.";
    std::array<std::uint8_t, feedback.size()> message{};
    std::ranges::copy(feedback, message.begin());
    std::array<std::uint8_t, feedback.size() + sealed_box::overhead> sealed{};
    std::array<std::uint8_t, feedback.size()> opened{};
    bool const ok = bob_public && sealed_box::seal(*bob_public, message, sealed) &&
                    sealed_box::open(*bob_public, bob_secret, sealed, opened) && opened == message;
    auto const name = sealed_box::backend_type::name;
    std::printf("sealed_box %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

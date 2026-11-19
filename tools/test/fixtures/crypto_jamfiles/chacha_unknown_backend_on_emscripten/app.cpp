// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names a type of its own as ChaCha20-Poly1305's backend stops where it makes the
// AEAD, with the backends that have the family.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>

#include <array>
#include <cstdint>

namespace {

/** A type of the program's own, which is no backend. */
struct my_backend {};

}  // namespace

int main() {
    std::array<std::uint8_t, 32> const key{};
    return webcpp::crypto::ciphers::chacha20_poly1305<my_backend>::make(key) ? 0 : 1;
}

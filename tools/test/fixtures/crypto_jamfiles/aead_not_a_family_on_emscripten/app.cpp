// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program for Emscripten that gives ciphers::aead a family that is no AEAD's, AES-GCM's.
#include <webcpp/crypto/backends/sodium.hpp>
#include <webcpp/crypto/ciphers/aead.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace crypto = webcpp::crypto;
    using aead = crypto::ciphers::aead<crypto::families::gcm, crypto::backends::sodium>;
    std::array<std::uint8_t, 32> const key{};
    return aead::from_key(key) ? 0 : 1;
}

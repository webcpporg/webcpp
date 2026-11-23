// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program for Emscripten that names OpenSSL, which is not built there, in ChaCha20-Poly1305's
// type.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace crypto = webcpp::crypto;
    std::array<std::uint8_t, 32> const key{};
    return crypto::ciphers::chacha20_poly1305<crypto::backends::openssl>::from_key(key) ? 0 : 1;
}

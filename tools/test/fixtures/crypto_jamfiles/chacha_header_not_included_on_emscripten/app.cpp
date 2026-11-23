// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names BearSSL in ChaCha20-Poly1305's type without including BearSSL's header stops
// where it makes the AEAD, with the header to include and the line that links BearSSL.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace crypto = webcpp::crypto;
    std::array<std::uint8_t, 32> const key{};
    return crypto::ciphers::chacha20_poly1305<crypto::backends::bearssl>::from_key(key) ? 0 : 1;
}

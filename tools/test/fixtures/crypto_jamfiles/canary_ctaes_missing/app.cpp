// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Makes an AES-256 block cipher on ctaes and encrypts one block: the program reads ctaes's
// canary, so that a library built other than by webcpp's third_party/Jamfile fails to link.
#include <webcpp/crypto/backends/ctaes.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 16> block{};
    auto aes = webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::ctaes>::from_key(key);
    return aes && aes->encrypt(block) ? 0 : 1;
}

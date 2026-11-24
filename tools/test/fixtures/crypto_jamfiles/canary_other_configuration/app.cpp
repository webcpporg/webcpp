// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Makes AES-256-GCM on BearSSL and seals one block: the program reads BearSSL's canary, so that
// a library built other than by webcpp's third_party/Jamfile fails to link.
#include <webcpp/crypto/backends/bearssl.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>
#include <webcpp/crypto/ciphers/gcm.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 12> const nonce{};
    std::array<std::uint8_t, 16> data{};
    auto aead = webcpp::crypto::ciphers::gcm<
        webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::bearssl>>::from_key(key);
    return aead && aead->seal(nonce, {}, data) ? 0 : 1;
}

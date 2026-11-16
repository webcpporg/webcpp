// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that uses the default backend, which on WebAssembly is BearSSL, and links none.
#include <webcpp/crypto/ciphers/aes256_gcm.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    return webcpp::crypto::ciphers::aes256_gcm::make(key) ? 0 : 1;
}

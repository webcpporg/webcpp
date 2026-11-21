// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that uses the AES block cipher's default backend, which on WebAssembly is ctaes, and
// links none.
#include <webcpp/crypto/ciphers/aes_block.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    return webcpp::crypto::ciphers::aes256<>::make(key) ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// As test/messages/chacha_default_not_linked, on Emscripten.

#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace ciphers = webcpp::crypto::ciphers;
    std::array<std::uint8_t, 32> const key{};
    return ciphers::chacha20_poly1305<>::make(key) &&
                   ciphers::chacha20_poly1305_original<>::make(key) &&
                   ciphers::xchacha20_poly1305<>::make(key)
               ? 0
               : 1;
}

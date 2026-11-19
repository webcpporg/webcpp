// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// As test/messages/box_default_not_linked, on Emscripten.

#include <webcpp/crypto/ciphers/secretbox.hpp>
#include <webcpp/crypto/hybrid/box.hpp>
#include <webcpp/crypto/hybrid/sealed_box.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace crypto = webcpp::crypto;
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 48> sealed{};
    return crypto::ciphers::secretbox<>::make(key) &&
                   crypto::ciphers::secretbox_xchacha20poly1305<>::make(key) &&
                   crypto::hybrid::box::make(key, key) &&
                   crypto::hybrid::box_xchacha20poly1305::make(key, key) &&
                   crypto::hybrid::sealed_box::seal(key, {}, sealed)
               ? 0
               : 1;
}

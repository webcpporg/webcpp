// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// The file of memory_two_files compiled without the memory option: it makes AES-256-GCM on
// OpenSSL, whose make differs from with.cpp's, and calls with.cpp's.
#include <webcpp/crypto/backends/openssl.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>
#include <webcpp/crypto/ciphers/gcm.hpp>

#include <array>
#include <cstdint>

bool make_with_the_option();

int main() {
    std::array<std::uint8_t, 32> const key{};
    auto const aead = webcpp::crypto::ciphers::gcm<
        webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::openssl>>::make(key);
    return aead && make_with_the_option() ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A user's program that names /webcpp/crypto//openssl: it prints the define the alias gives,
// then seals an empty message under the zero key of 32 bytes and the zero IV of 12 bytes
// with OpenSSL's AES-256-GCM, and prints the tag (McGrew and Viega's test case 13).

#include <webcpp/crypto/aes.hpp>
#include <webcpp/crypto/backends/openssl.hpp>
#include <webcpp/crypto/gcm.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <span>

int main() {
#if defined(WEBCPP_CRYPTO_HAS_OPENSSL)
    std::printf("HAS_OPENSSL=%d\n", WEBCPP_CRYPTO_HAS_OPENSSL);
#endif
    namespace crypto = webcpp::crypto;
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 12> const iv{};
    auto made = crypto::gcm<crypto::aes256<crypto::backends::openssl>>::make(key);
    if (!made) {
        return 1;
    }
    auto const tag = made->seal(iv, {}, std::span<std::uint8_t>());
    if (!tag) {
        return 1;
    }
    std::printf("tag ");
    for (std::uint8_t const b : *tag) {
        std::printf("%02x", static_cast<unsigned>(b));
    }
    std::printf("\n");
    return 0;
}

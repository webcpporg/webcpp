// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Sets the memory option and makes AES-256-GCM on OpenSSL, without the install, and defines no
// webcpp::crypto::openssl_memory_resource(): make's guard compares OpenSSL's functions with the
// adapter's address, which odr-uses the adapter, so the link fails naming the function (spec
// section 3.7).
#include <webcpp/crypto/backends/openssl.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>
#include <webcpp/crypto/ciphers/gcm.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    auto const aead = webcpp::crypto::ciphers::gcm<
        webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::openssl>>::make(key);
    return aead ? 0 : 1;
}

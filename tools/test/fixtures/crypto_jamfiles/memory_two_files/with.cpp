// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// The file of memory_two_files compiled with the memory option: it defines the program's
// resource, and makes AES-256-GCM on OpenSSL under the option.
#include <webcpp/crypto/backends/openssl.hpp>
#include <webcpp/crypto/ciphers/aes.hpp>
#include <webcpp/crypto/ciphers/gcm.hpp>

#include <array>
#include <cstdint>
#include <memory_resource>

std::pmr::memory_resource& webcpp::crypto::openssl_memory_resource() noexcept {
    return *std::pmr::new_delete_resource();
}

bool make_with_the_option() {
    std::array<std::uint8_t, 32> const key{};
    return webcpp::crypto::ciphers::gcm<
               webcpp::crypto::ciphers::aes256<webcpp::crypto::backends::openssl>>::make(key)
        .has_value();
}

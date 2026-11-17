// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Sends every allocation of OpenSSL's to the program's own resource, then seals and opens one
// block with AES-256-GCM on the default backend, OpenSSL natively when linked, and prints the
// backend that ran. The zero key and IV keep the output stable: a real program draws its key
// from random_device and never reuses an IV under it.
#include <webcpp/crypto/backends/openssl.hpp>
#include <webcpp/crypto/ciphers/aes256_gcm.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <memory_resource>

// Declared by crypto under WEBCPP_CRYPTO_OPENSSL_MEMORY_RESOURCE, defined once here. Never
// destroyed: OpenSSL frees through it after main returns.
std::pmr::memory_resource& webcpp::crypto::openssl_memory_resource() noexcept {
    // Never deleted, on purpose; a new that fails this early ends the program, which has no
    // resource for OpenSSL.
    // NOLINTNEXTLINE(cppcoreguidelines-owning-memory,bugprone-unhandled-exception-at-new)
    static auto* const resource = new std::pmr::synchronized_pool_resource;
    return *resource;
}

int main() {
    auto const installed = webcpp::crypto::backends::openssl::install_memory_functions();
    if (!installed) {
        std::printf("install: %s\n", installed.error().message().c_str());
        return 1;
    }
    std::array<std::uint8_t, 32> const key{};
    std::array<std::uint8_t, 12> const iv{};
    std::array<std::uint8_t, 16> data{};
    auto aead = webcpp::crypto::ciphers::aes256_gcm::make(key);
    if (!aead) {
        std::printf("make: %s\n", aead.error().message().c_str());
        return 1;
    }
    auto const tag = aead->seal(iv, {}, data);
    bool const ok = tag && aead->open(iv, {}, data, *tag) && data == std::array<std::uint8_t, 16>{};
    auto const name = webcpp::crypto::ciphers::aes256_gcm::backend_type::name;
    std::printf("aes256_gcm %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

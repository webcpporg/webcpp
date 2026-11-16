// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program over OpenSSL: HKDF (RFC 5869, A.1) and, where the backend has it,
// PBKDF2-HMAC-SHA-256 (RFC 7914, section 11, its first case).

#include <webcpp/hash/backends/openssl.hpp>
#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>
#include <webcpp/hash/pbkdf2.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <numeric>
#include <span>
#include <string_view>

namespace {

// Prints label, a space and bytes in lowercase hex, then a newline.
void print_hex(char const* label, std::span<std::uint8_t const> bytes) {
    std::printf("%s ", label);
    for (std::uint8_t const b : bytes) {
        std::printf("%02x", static_cast<unsigned>(b));
    }
    std::printf("\n");
}

// RFC 5869, appendix A.1: SHA-256, a 22-byte IKM, a 13-byte salt, a 10-byte info, 42 bytes.
std::array<std::uint8_t, 42> rfc5869_a1_okm() {
    std::array<std::uint8_t, 22> ikm{};
    ikm.fill(0x0b);
    std::array<std::uint8_t, 13> salt{};
    std::iota(salt.begin(), salt.end(), std::uint8_t{0x00});
    std::array<std::uint8_t, 10> info{};
    std::iota(info.begin(), info.end(), std::uint8_t{0xf0});
    std::array<std::uint8_t, 42> okm{};
    if (!webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::openssl>(
            okm, salt, ikm, info)) {
        okm.fill(0);
    }
    return okm;
}

}  // namespace

int main() {
    namespace hash = webcpp::hash;
#if defined(WEBCPP_HASH_HAS_OPENSSL)
    std::printf("HAS_OPENSSL=%d\n", WEBCPP_HASH_HAS_OPENSSL);
#endif
    print_hex("hkdf", rfc5869_a1_okm());
    std::string_view const password = "password";
    std::string_view const salt = "salt";
    std::array<std::uint8_t, 32> derived{};
    auto const done = hash::pbkdf2<hash::hmac_sha2_256, hash::backends::openssl>(
        derived, std::span(reinterpret_cast<std::uint8_t const*>(password.data()), password.size()),
        std::span(reinterpret_cast<std::uint8_t const*>(salt.data()), salt.size()), 1);
    print_hex("pbkdf2", derived);
    return done ? 0 : 1;
}

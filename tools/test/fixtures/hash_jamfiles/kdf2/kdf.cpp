// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program over BearSSL: HKDF (RFC 5869, A.1); BearSSL has no PBKDF2.

#include <webcpp/hash/backends/bearssl.hpp>
#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <numeric>
#include <span>

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
    if (!webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::bearssl>(
            okm, salt, ikm, info)) {
        okm.fill(0);
    }
    return okm;
}

}  // namespace

int main() {
    print_hex("hkdf", rfc5869_a1_okm());
    return 0;
}

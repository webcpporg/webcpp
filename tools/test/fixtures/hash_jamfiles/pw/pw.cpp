// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program over libsodium: Argon2id on the first case of libsodium's own table
// (test/default/pwhash_argon2id.c at 77e1ce5: its salt's first 16 bytes, its memory limit
// rounded down to a multiple of 1,024), scrypt on RFC 7914's second case, and HKDF (RFC 5869,
// A.1) on backends::sodium.

#include <webcpp/hash/argon2.hpp>
#include <webcpp/hash/backends/sodium.hpp>
#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>
#include <webcpp/hash/scrypt.hpp>

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
    if (!webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::sodium>(
            okm, salt, ikm, info)) {
        okm.fill(0);
    }
    return okm;
}

std::span<std::uint8_t const> bytes(std::string_view text) {
    return {reinterpret_cast<std::uint8_t const*>(text.data()), text.size()};
}

}  // namespace

int main() {
    namespace hash = webcpp::hash;
    std::array<std::uint8_t, 127> const password{
        0xa3, 0x47, 0xae, 0x92, 0xbc, 0xe9, 0xf8, 0x0f, 0x6f, 0x59, 0x5a, 0x44, 0x80, 0xfc, 0x9c,
        0x2f, 0xe7, 0xe7, 0xd7, 0x14, 0x8d, 0x37, 0x1e, 0x94, 0x87, 0xd7, 0x5f, 0x5c, 0x23, 0x00,
        0x8f, 0xfa, 0xe0, 0x65, 0x57, 0x7a, 0x92, 0x8f, 0xeb, 0xd9, 0xb1, 0x97, 0x3a, 0x5a, 0x95,
        0x07, 0x3a, 0xcd, 0xbe, 0xb6, 0xa0, 0x30, 0xcf, 0xc0, 0xd7, 0x9c, 0xaa, 0x2d, 0xc5, 0xcd,
        0x01, 0x1c, 0xef, 0x02, 0xc0, 0x8d, 0xa2, 0x32, 0xd7, 0x6d, 0x52, 0xdf, 0xbc, 0xa3, 0x8c,
        0xa8, 0xdc, 0xbd, 0x66, 0x5b, 0x17, 0xd1, 0x66, 0x5f, 0x7c, 0xf5, 0xfe, 0x59, 0x77, 0x2e,
        0xc9, 0x09, 0x73, 0x3b, 0x24, 0xde, 0x97, 0xd6, 0xf5, 0x8d, 0x22, 0x0b, 0x20, 0xc6, 0x0d,
        0x7c, 0x07, 0xec, 0x1f, 0xd9, 0x3c, 0x52, 0xc3, 0x10, 0x20, 0x30, 0x0c, 0x6c, 0x1f, 0xac,
        0xd7, 0x79, 0x37, 0xa5, 0x97, 0xc7, 0xa6};
    std::array<std::uint8_t, 16> const salt{0x55, 0x41, 0xfb, 0xc9, 0x95, 0xd5, 0xc1, 0x97,
                                            0xba, 0x29, 0x03, 0x46, 0xd2, 0xc5, 0x59, 0xde};
    std::array<std::uint8_t, 155> tag{};
    auto const argon2 = hash::argon2id(tag, password, salt, {5, 7256064});
    print_hex("argon2id", tag);

    std::array<std::uint8_t, 64> scrypted{};
    auto const scrypt = hash::scrypt(scrypted, bytes("password"), bytes("NaCl"), {1024, 8, 16});
    print_hex("scrypt", scrypted);

    print_hex("hkdf", rfc5869_a1_okm());
    return argon2 && scrypt ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// One program over every C library of webcpp::hash its target has: Keccak-256 and BLAKE3 of
// nothing, then HKDF (RFC 5869, A.1) on each linked backend and on the default backend. Each
// library is one archive, linked once; their symbols do not collide.

#include <webcpp/hash.hpp>

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

template <class Backend>
std::array<std::uint8_t, 42> rfc5869_a1_okm() {
    std::array<std::uint8_t, 22> ikm{};
    ikm.fill(0x0b);
    std::array<std::uint8_t, 13> salt{};
    std::iota(salt.begin(), salt.end(), std::uint8_t{0x00});
    std::array<std::uint8_t, 10> info{};
    std::iota(info.begin(), info.end(), std::uint8_t{0xf0});
    std::array<std::uint8_t, 42> okm{};
    if (!webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, Backend>(okm, salt, ikm, info)) {
        okm.fill(0);
    }
    return okm;
}

}  // namespace

int main() {
    namespace hash = webcpp::hash;
    hash::keccak_256 keccak;
    print_hex("keccak_256", keccak.result());
    hash::blake3 blake;
    print_hex("blake3", blake.result());
    print_hex("hkdf hash2", rfc5869_a1_okm<hash::backends::hash2>());
    print_hex("hkdf sodium", rfc5869_a1_okm<hash::backends::sodium>());
    print_hex("hkdf bearssl", rfc5869_a1_okm<hash::backends::bearssl>());
#if defined(WEBCPP_HASH_HAS_OPENSSL)
    print_hex("hkdf openssl", rfc5869_a1_okm<hash::backends::openssl>());
#endif
    print_hex("hkdf default", rfc5869_a1_okm<hash::default_kdf_backend<hash::hmac_sha2_256>>());
    return 0;
}

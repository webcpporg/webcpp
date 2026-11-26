// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals the XChaCha20-Poly1305 draft's example (appendix A.3.1) on the default backend, checks
// the tag and the ciphertext's first bytes against the draft's, opens it again, and prints the
// backend that ran. The key and nonce are the draft's: a real program draws its key from
// random_device; a 24-byte nonce drawn at random is safe.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string_view>

int main() {
    using aead = webcpp::crypto::ciphers::xchacha20_poly1305<>;
    // The key 0x80, 0x81, ..., 0x9f.
    std::array<std::uint8_t, 32> key{};
    for (std::size_t index = 0; index < key.size(); ++index) {
        key[index] = static_cast<std::uint8_t>(0x80 + index);
    }
    // The nonce 0x40, 0x41, ..., 0x57.
    std::array<std::uint8_t, 24> nonce{};
    for (std::size_t index = 0; index < nonce.size(); ++index) {
        nonce[index] = static_cast<std::uint8_t>(0x40 + index);
    }
    // NOLINTBEGIN(readability-trailing-comma): it asks a list of one row, wrapped, for the comma
    // and refuses it once clang-format puts the brace on a line of its own
    std::array<std::uint8_t, 12> const associated_data{0x50, 0x51, 0x52, 0x53, 0xc0, 0xc1,
                                                       0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7};
    // NOLINTEND(readability-trailing-comma)
    constexpr std::string_view sunscreen =
        "Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the "
        "future, sunscreen would be it.";
    std::array<std::uint8_t, sunscreen.size()> plaintext{};
    std::ranges::copy(sunscreen, plaintext.begin());
    auto data = plaintext;
    std::array<std::uint8_t, 16> const expected_tag{
        0xc0, 0x87, 0x59, 0x24, 0xc1, 0xc7, 0x98, 0x79,
        0x47, 0xde, 0xaf, 0xd8, 0x78, 0x0a, 0xcf, 0x49,
    };
    std::array<std::uint8_t, 8> const expected_head{0xbd, 0x6d, 0x17, 0x9d, 0x3e, 0x83, 0xd4, 0x3b};
    auto sealer = aead::from_key(key);
    bool ok = false;
    if (sealer) {
        auto const tag = sealer->seal(nonce, associated_data, data);
        ok = tag && webcpp::secure::constant_time_equal(*tag, expected_tag) &&
             std::equal(expected_head.begin(), expected_head.end(), data.begin()) &&
             sealer->open(nonce, associated_data, data, expected_tag) && data == plaintext;
    }
    auto const name = aead::backend_type::name;
    std::printf("xchacha20_poly1305 %s backend=%.*s\n", ok ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return ok ? 0 : 1;
}

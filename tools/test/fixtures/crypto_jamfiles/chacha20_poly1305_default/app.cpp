// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals RFC 8439's ChaCha20-Poly1305 example (section 2.8.2) on the default backend, checks the
// tag and the ciphertext's first bytes against the RFC's, opens it again, and prints the backend
// that ran. The key and nonce are the RFC's: a real program draws its key from random_device and
// never reuses a nonce under it.
#include <webcpp/crypto/ciphers/chacha20_poly1305.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string_view>

int main() {
    using aead = webcpp::crypto::ciphers::chacha20_poly1305<>;
    // The key 0x80, 0x81, ..., 0x9f.
    std::array<std::uint8_t, 32> key{};
    for (std::size_t index = 0; index < key.size(); ++index) {
        key[index] = static_cast<std::uint8_t>(0x80 + index);
    }
    // NOLINTBEGIN(readability-trailing-comma): it asks a list of one row, wrapped, for the comma
    // and refuses it once clang-format puts the brace on a line of its own
    std::array<std::uint8_t, 12> const nonce{0x07, 0x00, 0x00, 0x00, 0x40, 0x41,
                                             0x42, 0x43, 0x44, 0x45, 0x46, 0x47};
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
        0x1a, 0xe1, 0x0b, 0x59, 0x4f, 0x09, 0xe2, 0x6a,
        0x7e, 0x90, 0x2e, 0xcb, 0xd0, 0x60, 0x06, 0x91,
    };
    std::array<std::uint8_t, 8> const expected_head{0xd3, 0x1a, 0x8d, 0x34, 0x64, 0x8e, 0x60, 0xdb};
    auto sealer = aead::from_key(key);
    bool ok = false;
    if (sealer) {
        auto const tag = sealer->seal(nonce, associated_data, data);
        ok = tag && webcpp::secure::constant_time_equal(*tag, expected_tag) &&
             std::equal(expected_head.begin(), expected_head.end(), data.begin()) &&
             sealer->open(nonce, associated_data, data, expected_tag) && data == plaintext;
    }
    auto const name = aead::backend_type::name;
    std::printf("chacha20_poly1305 %s backend=%.*s\n", ok ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return ok ? 0 : 1;
}

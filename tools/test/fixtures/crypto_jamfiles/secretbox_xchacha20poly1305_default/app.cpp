// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals a case of libsodium's XChaCha20 secret boxes (test/default/xchacha20.c) on the default
// backend, checks the tag and the ciphertext against the test's, opens it again, and prints the
// backend that ran. The key and nonce are the test's: a real program draws its key from
// random_device, and a 24-byte nonce drawn at random for every message is safe.
#include <webcpp/crypto/constant_time_equal.hpp>
#include <webcpp/crypto/secret_key_encryption/secretbox.hpp>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string_view>

namespace {

// The bytes of a string of lower-case hex digits, two per byte.
template <std::size_t Size>
std::array<std::uint8_t, Size> from_hex(std::string_view hex) {
    std::array<std::uint8_t, Size> bytes{};
    for (std::size_t index = 0; index < Size; ++index) {
        auto const digit = [&](std::size_t at) {
            char const c = hex[at];
            return static_cast<unsigned>(c <= '9' ? c - '0' : c - 'a' + 10);
        };
        bytes[index] = static_cast<std::uint8_t>((digit(2 * index) << 4U) | digit((2 * index) + 1));
    }
    return bytes;
}

}  // namespace

int main() {
    using secretbox = webcpp::crypto::secret_key_encryption::secretbox_xchacha20poly1305<>;
    auto const key =
        from_hex<32>("10c0ad4054b48d7d1de1d9ab6f782ca883d886573e9d18c1d47b6ee6b5208189");
    auto const nonce = from_hex<24>("977edf57428d0e0247a3c88c9a9ec321bbaae1a4da8353b5");
    auto const plaintext = from_hex<21>("518e4a27949812424b2a381c3efea6055ee5e75eff");
    auto const expected_tag = from_hex<16>("0c801a037c2ed0500d6ef68e8d195ece");
    auto const expected = from_hex<21>("b05a15f8edb68b35773e81ac2aca18e9be53416f9a");
    auto data = plaintext;
    auto sealer = secretbox::from_key(key);
    bool ok = false;
    if (sealer) {
        auto const tag = sealer->seal(nonce, data);
        ok = tag && webcpp::crypto::constant_time_equal(*tag, expected_tag) && data == expected &&
             sealer->open(nonce, data, expected_tag) && data == plaintext;
    }
    auto const name = secretbox::backend_type::name;
    std::printf("secretbox_xchacha20poly1305 %s backend=%.*s\n", ok ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return ok ? 0 : 1;
}

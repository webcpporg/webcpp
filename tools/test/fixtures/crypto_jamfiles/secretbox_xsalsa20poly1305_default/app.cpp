// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals NaCl's secret box (libsodium's test/default/secretbox.c) on the default backend, checks
// the tag and the ciphertext's first bytes against secretbox.exp, opens it again, and prints the
// backend that ran. The key and nonce are the test's: a real program draws its key from
// random_device, and a 24-byte nonce drawn at random for every message is safe.
#include <webcpp/crypto/secret_key_encryption/secretbox.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <algorithm>
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
    using secretbox = webcpp::crypto::secret_key_encryption::secretbox<>;
    auto const key =
        from_hex<32>("1b27556473e985d462cd51197a9a46c76009549eac6474f206c4ee0844f68389");
    auto const nonce = from_hex<24>("69696ee955b62b73cd62bda875fc73d68219e0036b7a0b37");
    auto const plaintext = from_hex<131>(
        "be075fc53c81f2d5cf141316ebeb0c7b5228c52a4c62cbd44b66849b64244ffce5ecbaaf33bd751a1ac7"
        "28d45e6c61296cdc3c01233561f41db66cce314adb310e3be8250c46f06dceea3a7fa1348057e2f6556a"
        "d6b1318a024a838f21af1fde048977eb48f59ffd4924ca1c60902e52f0a089bc76897040e082f9377638"
        "48645e0705");
    auto const expected_tag = from_hex<16>("f3ffc7703f9400e52a7dfb4b3d3305d9");
    auto const expected_head = from_hex<8>("8e993b9f48681273");
    auto data = plaintext;
    auto sealer = secretbox::from_key(key);
    bool ok = false;
    if (sealer) {
        auto const tag = sealer->seal(nonce, data);
        ok = tag && webcpp::secure::constant_time_equal(*tag, expected_tag) &&
             std::equal(expected_head.begin(), expected_head.end(), data.begin()) &&
             sealer->open(nonce, data, expected_tag) && data == plaintext;
    }
    auto const name = secretbox::backend_type::name;
    std::printf("secretbox %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Seals NaCl's box (libsodium's test/default/box.c) from Alice to Bob on the default
// backend, checks the tag and the ciphertext's first bytes against box.exp, opens it with Bob's
// keys (box2.c), each an X25519 key pair and the peer's public key, and prints the backend that
// ran. The keys and nonce are the test's: a real program draws its key pair with generate(), and
// a nonce at random for every message.
#include <webcpp/crypto/constant_time_equal.hpp>
#include <webcpp/crypto/curves/x25519.hpp>
#include <webcpp/crypto/public_key_encryption/box.hpp>

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
    using webcpp::crypto::public_key_encryption::box;
    auto const alice_secret =
        from_hex<32>("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a");
    auto const alice_public =
        from_hex<32>("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a");
    auto const bob_secret =
        from_hex<32>("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb");
    auto const bob_public =
        from_hex<32>("de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f");
    auto const nonce = from_hex<24>("69696ee955b62b73cd62bda875fc73d68219e0036b7a0b37");
    auto const plaintext = from_hex<131>(
        "be075fc53c81f2d5cf141316ebeb0c7b5228c52a4c62cbd44b66849b64244ffce5ecbaaf33bd751a1ac7"
        "28d45e6c61296cdc3c01233561f41db66cce314adb310e3be8250c46f06dceea3a7fa1348057e2f6556a"
        "d6b1318a024a838f21af1fde048977eb48f59ffd4924ca1c60902e52f0a089bc76897040e082f9377638"
        "48645e0705");
    auto const expected_tag = from_hex<16>("f3ffc7703f9400e52a7dfb4b3d3305d9");
    auto const expected_head = from_hex<8>("8e993b9f48681273");
    auto data = plaintext;
    namespace x25519 = webcpp::crypto::curves::x25519;
    auto const alice_pair = x25519::keypair::from_secret(alice_secret);
    auto const bob_pair = x25519::keypair::from_secret(bob_secret);
    auto const alice_key = x25519::public_key::from_bytes(alice_public);
    auto const bob_key = x25519::public_key::from_bytes(bob_public);
    bool ok = false;
    if (!alice_pair || !bob_pair || !alice_key || !bob_key) {
        std::printf("box FAILED\n");
        return 1;
    }
    auto alice = box::from_keys(*alice_pair, *bob_key);
    auto bob = box::from_keys(*bob_pair, *alice_key);
    if (alice && bob) {
        auto const sealed = alice->seal(nonce, data);
        ok = sealed && webcpp::crypto::constant_time_equal(*sealed, expected_tag) &&
             std::equal(expected_head.begin(), expected_head.end(), data.begin()) &&
             bob->open(nonce, data, *sealed) && data == plaintext;
    }
    auto const name = box::backend_type::name;
    std::printf("box %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

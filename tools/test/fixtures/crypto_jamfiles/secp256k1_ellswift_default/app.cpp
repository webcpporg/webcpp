// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Makes the ElligatorSwift encodings of two fixed key pairs on ElligatorSwift's default backend,
// checks that each decodes to its key pair's public key and that both sides of BIP 324's
// exchange agree, and prints the backend that ran. The secrets and the randomness are fixed: a
// real program draws its own, and never prints a shared secret.
#include <webcpp/crypto/curves/secp256k1.hpp>
#include <webcpp/crypto/curves/secp256k1/ellswift.hpp>
#include <webcpp/secure/constant_time_equal.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

namespace {

std::array<std::uint8_t, 32> repeated(std::uint8_t value) {
    std::array<std::uint8_t, 32> bytes{};
    bytes.fill(value);
    return bytes;
}

}  // namespace

int main() {
    namespace crypto = webcpp::crypto;
    namespace secure = webcpp::secure;
    namespace secp256k1 = webcpp::crypto::curves::secp256k1;
    auto const initiator = secp256k1::keypair::from_secret(repeated(0x11));
    auto const responder = secp256k1::keypair::from_secret(repeated(0x22));
    bool ok = false;
    if (initiator && responder) {
        auto const sent = secp256k1::ellswift_create(*initiator, repeated(0x33));
        auto const received = secp256k1::ellswift_create(*responder, repeated(0x44));
        auto const initiator_key = initiator->public_key();
        auto const responder_key = responder->public_key();
        if (sent && received && initiator_key && responder_key &&
            secp256k1::ellswift_decode(*sent) == *initiator_key &&
            secp256k1::ellswift_decode(*received) == *responder_key) {
            auto const mine = secp256k1::ellswift_xdh(*initiator, *sent, *received,
                                                      secp256k1::ellswift_party::initiator);
            auto const theirs = secp256k1::ellswift_xdh(*responder, *sent, *received,
                                                        secp256k1::ellswift_party::responder);
            ok = mine && theirs && secure::constant_time_equal(mine->bytes(), theirs->bytes());
        }
    }
    auto const name = crypto::default_backend_t<crypto::families::secp256k1_ellswift>::name;
    std::printf("ellswift %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}

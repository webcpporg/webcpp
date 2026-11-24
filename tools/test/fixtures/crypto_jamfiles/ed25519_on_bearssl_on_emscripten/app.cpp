// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names BearSSL, which has no Ed25519, in an Ed25519 key pair's type.
#include <webcpp/crypto/curves/ed25519.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const seed{};
    return webcpp::crypto::curves::ed25519::basic_keypair<
               webcpp::crypto::backends::bearssl>::from_secret(seed)
               ? 0
               : 1;
}

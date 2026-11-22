// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that makes a P-256 key pair on its default backend, BearSSL, and links none.
#include <webcpp/crypto/curves/p256.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> scalar{};
    scalar.back() = 1;
    return webcpp::crypto::curves::p256::keypair::make(scalar) ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that agrees an X25519 shared secret on its default backend, libsodium on every target,
// without linking it, stops where it calls it, with the line that links libsodium, the one backend
// that has it (design D32).
#include <webcpp/crypto/curves/x25519.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> const key{};
    return webcpp::crypto::curves::x25519::agree(key, key) ? 0 : 1;
}

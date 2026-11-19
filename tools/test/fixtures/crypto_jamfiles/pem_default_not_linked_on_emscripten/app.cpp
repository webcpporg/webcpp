// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that armours DER as PEM on its default backend, libsodium on every target, without
// linking it, stops where it calls it, with the line that links libsodium, the one backend that has
// it (design D32).
#include <webcpp/crypto/pem.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 1> const der{};
    std::array<char, 128> out{};
    return webcpp::crypto::pem::armour("A", der, out) ? 0 : 1;
}

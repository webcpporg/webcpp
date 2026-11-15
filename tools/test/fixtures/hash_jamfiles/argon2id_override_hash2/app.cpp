// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// An override of argon2id's default backend is honoured (spec 4.1), even with libsodium linked:
// WEBCPP_HASH_DEFAULT_BACKEND_ARGON2ID_HASH2 and a call that names no backend stop with
// backends::hash2's refusal of spec 3.3, and with no other error.

#include <webcpp/hash/argon2.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 16> salt{};
    auto done = webcpp::hash::argon2id(output, {}, salt, webcpp::hash::argon2id_interactive);
    return done ? 0 : 1;
}

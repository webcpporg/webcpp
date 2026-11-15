// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// An override of scrypt's default backend is honoured (spec 4.1), even with libsodium linked:
// WEBCPP_HASH_DEFAULT_BACKEND_SCRYPT_HASH2 and a call that names no backend stop with
// backends::hash2's refusal of spec 3.3, and with no other error.

#include <webcpp/hash/scrypt.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 64> output{};
    auto done = webcpp::hash::scrypt(output, {}, {}, {.n = 16, .r = 1, .p = 1});
    return done ? 0 : 1;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// bcrypt named on backends::hash2, which has no bcrypt, stops naming the backend that has it
// (spec 3.3, the row of doc/capabilities.json).

#include <webcpp/hash/backends/hash2.hpp>
#include <webcpp/hash/bcrypt.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<char, webcpp::hash::bcrypt_hash_size> output{};
    std::array<std::uint8_t, webcpp::hash::bcrypt_salt_size> const salt{};
    auto const done = webcpp::hash::bcrypt<webcpp::hash::backends::hash2>(output, {}, salt);
    return done ? 0 : 1;
}

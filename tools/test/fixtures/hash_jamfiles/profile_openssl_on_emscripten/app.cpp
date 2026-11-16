// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that derives with HKDF on the default backend: the define its Jamfile gives stops
// it on Emscripten, where webcpp builds no OpenSSL.

#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 4> const input{};
    auto const done = webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256>(output, input, input, input);
    return done ? 0 : 1;
}

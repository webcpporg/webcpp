// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// backends::webcrypto named in a synchronous function stops with spec 11.2's text, on every target
// (ruling R77, C-m4): only the asynchronous family takes it.

#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 4> input{};
    auto done = webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::webcrypto>(
        output, input, input, input);
    return done ? 0 : 1;
}

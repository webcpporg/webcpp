// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// An override whose backend lacks the function over the hmac used (spec 4.1):
// WEBCPP_HASH_DEFAULT_BACKEND_HKDF_SODIUM and hkdf over hmac_sha2_384 stop with libsodium's
// text of spec 3.3, and with no other error.

#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 48> output{};
    std::array<std::uint8_t, 4> input{};
    auto done = webcpp::hash::hkdf<webcpp::hash::hmac_sha2_384>(output, input, input, input);
    return done ? 0 : 1;
}

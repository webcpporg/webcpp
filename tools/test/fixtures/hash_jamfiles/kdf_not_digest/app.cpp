// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A key derivation over an hmac whose result is not a digest (FNV-1a's is a 64-bit integer)
// stops with spec section 3.3's text, and with no other error.

#include <webcpp/hash/hkdf.hpp>

#include <boost/hash2/fnv1a.hpp>
#include <boost/hash2/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 4> input{};
    auto done =
        webcpp::hash::hkdf<boost::hash2::hmac<boost::hash2::fnv1a_64>>(output, input, input, input);
    return done ? 0 : 1;
}

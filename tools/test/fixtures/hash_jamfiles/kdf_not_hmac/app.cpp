// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// hkdf_extract, whose result is the hmac's result_type, over a type that has none stops with
// spec section 3.3's text too, and with no "no matching function" error.

#include <webcpp/hash/hkdf.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 4> input{};
    auto prk = webcpp::hash::hkdf_extract<int>(input, input);
    return prk ? 0 : 1;
}

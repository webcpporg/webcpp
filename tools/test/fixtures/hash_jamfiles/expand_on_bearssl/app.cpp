// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// hkdf_expand on backends::bearssl, whose br_hkdf_* keeps the PRK inside its context, stops with
// spec section 3.3's text, and with no other error.

#include <webcpp/hash/backends/bearssl.hpp>
#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 32> prk{};
    auto done =
        webcpp::hash::hkdf_expand<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::bearssl>(
            output, prk, prk);
    return done ? 0 : 1;
}

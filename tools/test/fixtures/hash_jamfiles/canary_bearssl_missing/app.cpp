// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Derives 42 bytes with HKDF on backends::bearssl: the program reads the canary of
// /third_party//bearssl, so that a library missing from the link, or built at another commit, fails
// to link with the canary's name (spec 5.4).

#include <webcpp/hash/backends/bearssl.hpp>
#include <webcpp/hash/hkdf.hpp>
#include <webcpp/hash/hmac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 42> okm{};
    std::array<std::uint8_t, 22> const ikm{};
    auto const done =
        webcpp::hash::hkdf<webcpp::hash::hmac_sha2_256, webcpp::hash::backends::bearssl>(okm, {},
                                                                                         ikm, {});
    return done ? 0 : 1;
}

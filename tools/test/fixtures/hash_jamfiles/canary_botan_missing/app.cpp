// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Hashes "abc" with Whirlpool on backends::botan: the program reads the canary of
// /third_party//botan, so that a library missing from the link, or built at another commit, fails
// to link with the canary's name (spec 5.4).

#include <webcpp/hash/backends/botan.hpp>
#include <webcpp/hash/digest.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 3> const abc{0x61, 0x62, 0x63};
    std::array<std::uint8_t, 64> digest{};
    auto const done =
        webcpp::hash::digest_of<webcpp::hash::digests::whirlpool, webcpp::hash::backends::botan>(
            digest, abc);
    return done ? 0 : 1;
}

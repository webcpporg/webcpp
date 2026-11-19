// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// digest_of over a tag whose default is backends::xkcp, in a program that does not link XKCP,
// stops with the instruction to add /third_party//xkcp (spec 5.7).

#include <webcpp/hash/digest.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    auto done = webcpp::hash::digest_of<webcpp::hash::digests::keccak_256>(output, {});
    return done ? 0 : 1;
}

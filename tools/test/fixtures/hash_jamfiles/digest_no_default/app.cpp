// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// digest_of over a tag with no default backend, on its default, stops: the call names its backend
// (design D34).

#include <webcpp/hash/digest.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 64> output{};
    auto done = webcpp::hash::digest_of<webcpp::hash::digests::whirlpool>(output, {});
    return done ? 0 : 1;
}

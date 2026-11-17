// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// digest_of over a tag the named backend does not have stops naming the backends that have it
// (spec 3.3, the tag's row of doc/capabilities.json).

#include <webcpp/hash/digest.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    auto done =
        webcpp::hash::digest_of<webcpp::hash::digests::blake3, webcpp::hash::backends::hash2>(
            output, {});
    return done ? 0 : 1;
}

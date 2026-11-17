// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// mac over a type that is not a tag of macs stops with the family's refusal (spec 3.3).

#include <webcpp/hash/mac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 32> output{};
    auto done = webcpp::hash::mac<int>(output, {}, {});
    return done ? 0 : 1;
}

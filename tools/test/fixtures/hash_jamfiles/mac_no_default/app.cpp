// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// mac over HMAC of a digest no backend has HMAC over, on its default, stops (design D34).

#include <webcpp/hash/mac.hpp>

#include <array>
#include <cstdint>

int main() {
    std::array<std::uint8_t, 64> output{};
    namespace hash = webcpp::hash;
    auto done = hash::mac<hash::macs::hmac<hash::digests::md5_sha1>>(output, {}, {});
    return done ? 0 : 1;
}

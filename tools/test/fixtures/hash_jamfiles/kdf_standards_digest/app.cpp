// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// sskdf over a digest SP 800-56C does not approve (MD5) and x963kdf over one outside FIPS 180-4
// (SHA3-256) stop, whatever the backend.

#include <webcpp/hash/kdf_standards.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace hash = webcpp::hash;
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 16> const secret{1};
    auto const sskdf = hash::sskdf<hash::digests::md5>(output, secret);
    auto const x963kdf = hash::x963kdf<hash::digests::sha3_256>(output, secret);
    return sskdf && x963kdf ? 0 : 1;
}

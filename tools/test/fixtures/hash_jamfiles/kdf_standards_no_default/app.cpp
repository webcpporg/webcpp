// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// kbkdf, sskdf and x963kdf on their default, which none of them has, stop (design D34).

#include <webcpp/hash/hmac.hpp>
#include <webcpp/hash/kdf_standards.hpp>

#include <array>
#include <cstdint>

int main() {
    namespace hash = webcpp::hash;
    std::array<std::uint8_t, 32> output{};
    std::array<std::uint8_t, 16> const key{1};
    auto const kbkdf = hash::kbkdf<hash::hmac_sha2_256>(output, key);
    auto const sskdf = hash::sskdf<hash::digests::sha2_256>(output, key);
    auto const x963kdf = hash::x963kdf<hash::digests::sha2_256>(output, key);
    return kbkdf && sskdf && x963kdf ? 0 : 1;
}

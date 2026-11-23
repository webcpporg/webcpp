// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// As test/messages/box_not_a_family, on Emscripten.

#include <webcpp/crypto/public_key_encryption/box.hpp>

#include <array>
#include <cstdint>

namespace {

/** A type that names no family, and so has no default backend. */
struct not_a_family {};

}  // namespace

int main() {
    std::array<std::uint8_t, 32> const key{};
    using box = webcpp::crypto::public_key_encryption::basic_box<not_a_family>;
    return box::from_keys(key, key) ? 0 : 1;
}

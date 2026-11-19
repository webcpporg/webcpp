// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names a policy of its own in Ed25519's verify, on its default backend linked,
// stops where it calls it, with the one policy there is.
#include <webcpp/crypto/curves/ed25519.hpp>

#include <array>
#include <cstdint>

namespace {

/** A verification policy of the program's own. */
struct lenient {};

}  // namespace

int main() {
    std::array<std::uint8_t, 32> const public_key{};
    std::array<std::uint8_t, 64> const signature{};
    return webcpp::crypto::curves::ed25519::verify<lenient>(public_key, {}, signature) ? 0 : 1;
}

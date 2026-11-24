// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names a policy of its own in Ed25519's crypto::verify, on its default backend
// linked, stops where it calls it, with the one policy there is.
#include <webcpp/crypto/curves/ed25519.hpp>
#include <webcpp/crypto/signing.hpp>

#include <array>
#include <cstdint>
#include <span>

namespace {

/** A verification policy of the program's own. */
struct lenient {};

}  // namespace

int main() {
    auto const public_key =
        webcpp::crypto::curves::ed25519::public_key::from_bytes(std::array<std::uint8_t, 32>{});
    webcpp::crypto::curves::ed25519::signature const signature{};
    return public_key &&
                   webcpp::crypto::verify(webcpp::crypto::eddsa, signature,
                                          std::span<std::uint8_t const>{}, *public_key, lenient{})
               ? 0
               : 1;
}

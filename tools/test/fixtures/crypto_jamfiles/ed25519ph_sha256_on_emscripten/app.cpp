// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names SHA-256 in Ed25519ph's type, which RFC 8032 defines over SHA-512.
#include <webcpp/crypto/curves/ed25519.hpp>
#include <webcpp/hash/algorithms.hpp>

int main() {
    return webcpp::crypto::curves::ed25519::ph<webcpp::hash::sha2_256>::begin() ? 0 : 1;
}

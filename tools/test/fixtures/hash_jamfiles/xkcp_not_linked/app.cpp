// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names keccak_256 and does not link XKCP stops with the instruction to add
// /third_party//xkcp (spec section 5.7, the first row).

#include <webcpp/hash/keccak.hpp>

int main() {
    return 0;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that uses blake3 without linking /third_party//blake3 stops with the instruction to
// add it (spec 5.7, the second row).

#include <webcpp/hash/blake3.hpp>

int main() {
    return 0;
}

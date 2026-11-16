// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names backends::sodium and does not link libsodium stops with the instruction to
// add /third_party//sodium (spec section 5.7, the third row).

#include <webcpp/hash/backends/sodium.hpp>

int main() {
    return 0;
}

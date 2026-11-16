// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program that names backends::openssl without linking /webcpp/hash//openssl stops with the
// instruction to add it (spec 5.7, the fifth row).

#include <webcpp/hash/backends/openssl.hpp>

int main() {
    return 0;
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Two overrides of HKDF's default backend (spec 4.1) stop the build with an #error naming both
// defines.

#include <webcpp/hash/kdf.hpp>

int main() {
    return 0;
}

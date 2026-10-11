// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Suspends, then ends with std::exit(0), without exit_status.

#include <emscripten.h>

#include <cstdlib>

int main() {
    emscripten_sleep(10);
    std::exit(0);
}

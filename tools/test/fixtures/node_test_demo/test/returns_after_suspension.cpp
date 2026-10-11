// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Suspends, then returns WEBCPP_TEST_STATUS from main, without exit_status.

#include <emscripten.h>

int main() {
    emscripten_sleep(10);
    return WEBCPP_TEST_STATUS;
}

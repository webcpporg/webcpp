// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Suspends, then ends with 0 through exit_status, which keeps it on both variants.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>

int main() {
    emscripten_sleep(10);
    return webcpp::test::exit_status(0);
}

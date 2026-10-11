// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Asks for a bound of WEBCPP_TEST_BOUND seconds, outside 1 to 2147483, which is refused.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>

#include <chrono>

int main() {
    webcpp::test::bound(std::chrono::seconds(WEBCPP_TEST_BOUND));
    emscripten_sleep(5000);
    return webcpp::test::exit_status(0);
}

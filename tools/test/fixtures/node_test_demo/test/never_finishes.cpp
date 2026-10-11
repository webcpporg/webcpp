// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Waits far past its bound of 3 s, which stops it.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>

#include <chrono>

int main() {
    webcpp::test::bound(std::chrono::seconds(3));
    emscripten_sleep(600000);
    return webcpp::test::exit_status(0);
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Ends with 0 through exit_status while a timer of 300 s is pending, which must not hold it.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>
#include <emscripten/em_js.h>

// clang-format off
EM_JS(void, wait_300_s, (), {
    setTimeout(() => {}, 300000);
});
// clang-format on

int main() {
    wait_300_s();
    emscripten_sleep(10);
    return webcpp::test::exit_status(0);
}

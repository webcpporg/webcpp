// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Ends with 3 through exit_status, while a callback that would end with 0 and a write of
// process.exitCode = 0 are still to come.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>
#include <emscripten/em_js.h>
#include <emscripten/eventloop.h>

// clang-format off
EM_JS(void, write_zero_later, (), {
    setTimeout(() => {
        process.exitCode = 0;
    }, 50);
});
// clang-format on

namespace {

void end_with_zero(void*) {
    (void)webcpp::test::exit_status(0);
}

}  // namespace

int main() {
    emscripten_set_timeout(end_with_zero, 50, nullptr);
    write_zero_later();
    emscripten_sleep(10);
    return webcpp::test::exit_status(3);
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Ends with 0 through exit_status with nothing pending, and says so when node, its loop empty,
// emits beforeExit, which it never emits on a call of process.exit.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>
#include <emscripten/em_js.h>

// clang-format off
EM_JS(void, say_when_node_ends_on_its_own, (), {
    process.once('beforeExit', () => {
        process.stdout.write('node ended on its own\n');
    });
});
// clang-format on

int main() {
    say_when_node_ends_on_its_own();
    emscripten_sleep(10);
    return webcpp::test::exit_status(0);
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Awaits a promise that nothing settles, with nothing else to keep node alive: main never ends.

#include <webcpp/test/exit_status.hpp>

#include <emscripten/em_js.h>

// clang-format off
EM_ASYNC_JS(void, await_forever, (), {
    await new Promise(() => {});
});
// clang-format on

int main() {
    await_forever();
    return webcpp::test::exit_status(0);
}

// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Ends with 3 through exit_status inside a coroutine that suspended, never through main.

#include <webcpp/test/exit_status.hpp>

#include <emscripten.h>

#include <coroutine>
#include <exception>

namespace {

/** A coroutine that runs to its end as it is called, and returns nothing. */
struct eager {
    struct promise_type {
        eager get_return_object() { return {}; }

        std::suspend_never initial_suspend() noexcept { return {}; }

        std::suspend_never final_suspend() noexcept { return {}; }

        void return_void() {}

        void unhandled_exception() { std::terminate(); }
    };
};

eager sleep_then_exit() {
    emscripten_sleep(10);
    (void)webcpp::test::exit_status(3);
    co_return;
}

}  // namespace

int main() {
    sleep_then_exit();
    return webcpp::test::exit_status(0);
}

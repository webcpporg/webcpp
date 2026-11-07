// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// GCC PR121643: await_suspend with an additional default argument crashed GCC
// 15.2. Compile and run this after installation and every toolchain cache restore.
#include <coroutine>

struct task {
    struct promise_type {
        task get_return_object() { return {}; }

        std::suspend_never initial_suspend() noexcept { return {}; }

        std::suspend_never final_suspend() noexcept { return {}; }

        void return_void() {}

        void unhandled_exception() { __builtin_trap(); }
    };
};

struct operation {
    int& result;

    bool await_ready() const { return false; }

    bool await_suspend(std::coroutine_handle<>, const int& value = 42) {
        result = value;
        return false;
    }

    void await_resume() const {}
};

task exercise(int& result) {
    co_await operation{result};
}

int main() {
    int result = 0;
    exercise(result);
    return result == 42 ? 0 : 1;
}

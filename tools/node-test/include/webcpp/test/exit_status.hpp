// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// How a test ends under webcpp's test support (tools/node-test/node-pre.js), which every test
// and example links: natively a plain status, on emscripten a status the support keeps.

#ifndef WEBCPP_TEST_EXIT_STATUS_HPP
#define WEBCPP_TEST_EXIT_STATUS_HPP

#include <chrono>

#ifdef __EMSCRIPTEN__
#include <emscripten/em_asm.h>
#endif

namespace webcpp::test {

/**
 Gives status to webcpp's test support and returns it, so that main ends with it: natively
 the status is main's; on emscripten the support ends node with the first status it is given,
 on its next turn, whatever is still pending or runs later.

 Tip: it never calls std::exit, which under Emscripten's default EXIT_RUNTIME=0 neither ends
 node nor keeps the status from a later write, and in a debug build prints Emscripten's notice
 "program exited ..., but keepRuntimeAlive() is set"; and under Asyncify a main that suspended
 loses the value it returns, which the support already holds (Emscripten 6.0.11, node 26.7.0).
*/
[[nodiscard]] inline int exit_status(int status) {
#ifdef __EMSCRIPTEN__
    EM_ASM(
        {
            if (Module['webcppTestFinished']) {
                Module['webcppTestFinished']($0);
            }
        },
        status);
#endif
    return status;
}

/**
 Re-arms the bound of this test under node to limit, from now; natively does nothing.

 Tip: a limit outside 1 to 2147483 s, which node's timers cannot hold, stops the test with 1.
*/
inline void bound(std::chrono::seconds limit) {
#ifdef __EMSCRIPTEN__
    EM_ASM(
        {
            if (Module['webcppTestBound']) {
                Module['webcppTestBound']($0);
            }
        },
        static_cast<double>(limit.count()));
#else
    (void)limit;
#endif
}

}  // namespace webcpp::test

#endif  // WEBCPP_TEST_EXIT_STATUS_HPP

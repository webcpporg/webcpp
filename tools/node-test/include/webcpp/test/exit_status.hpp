// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// How a test ends under webcpp's test support (tools/node-test/node-pre.js), which every test
// and example links: natively a plain status, on emscripten an exit that node keeps.

#ifndef WEBCPP_TEST_EXIT_STATUS_HPP
#define WEBCPP_TEST_EXIT_STATUS_HPP

#include <chrono>
#include <cstdlib>

#ifdef __EMSCRIPTEN__
#include <emscripten/em_asm.h>
#endif

namespace webcpp::test {

/**
 Ends main with status: natively returns it; on emscripten gives it to webcpp's test support,
 which ends node with the first status it is given on its next turn, then exits.

 Tip: under Asyncify a main that suspended loses the value it returns, and node would exit 0;
 and std::exit alone leaves node running while anything is pending, so that a later write
 replaces the status (both measured with Emscripten 6.0.11 and node 26.7.0).
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
    std::exit(status);
#else
    return status;
#endif
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

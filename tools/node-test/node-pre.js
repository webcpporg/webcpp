// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// webcpp's test support under node, which every test and example on emscripten links
// (--pre-js, tools/webcpp.jam): a test whose main did not finish fails, and a test that runs
// past its bound is stopped. In a browser, which has no process, it does nothing.
if (typeof process === 'object' && typeof process.on === 'function') {
    let finished = false
    let watchdog = null
    const bound = seconds => {
        if (watchdog) {
            clearTimeout(watchdog)
        }
        watchdog = setTimeout(() => {
            process.stderr.write(`webcpp: the test ran past its bound of ${seconds} s\n`)
            process.exit(1)
        }, seconds * 1000)
        watchdog.unref()
    }
    bound(120)
    Module['webcppTestBound'] = bound
    Module['webcppTestFinished'] = () => {
        finished = true
    }
    // After main returned: under Asyncify a main that suspended returns early, unwound, and
    // Asyncify.currData is then set; that return is not main's end.
    Module['postRun'] = [].concat(Module['postRun'] ?? [], () => {
        if (typeof Asyncify === 'undefined' || !Asyncify.currData) {
            finished = true
        }
    })
    // A status other than 0 is a failure already; only a 0 that main never said is replaced.
    process.on('exit', () => {
        if (!finished && !process.exitCode) {
            process.exitCode = 1
            process.stderr.write('webcpp: main did not finish: it never returned, or it returned ' +
                'after a suspension under Asyncify, which loses the value; end it with ' +
                'webcpp::test::exit_status\n')
        }
    })
}

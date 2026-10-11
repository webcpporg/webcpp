// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// webcpp's test support under node, which every test and example on emscripten links
// (--pre-js, tools/webcpp.jam): a test whose main did not run or did not finish fails, a test
// that ends through webcpp::test::exit_status ends with the first status it gives, and a test
// that runs past its bound is stopped. In a browser, which has no process, it does nothing.
if (typeof process === 'object' && typeof process.on === 'function') {
    let finished = false
    // The first status exit_status gives, the test's own; null until then.
    let status = null
    let watchdog = null
    // The longest bound, in seconds: node fires a timer of more than 2^31 - 1 ms at once.
    const longest = 2147483
    const bound = seconds => {
        if (!(seconds >= 1 && seconds <= longest)) {
            process.stderr.write(`webcpp: the bound of ${seconds} s is outside 1 to ${longest} s\n`)
            process.exit(1)
        }
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
    // Node ends with the first status on its next turn, whatever is still pending or runs
    // later: a timer, a callback that gives another status, a write of process.exitCode.
    Module['webcppTestFinished'] = given => {
        finished = true
        if (status === null) {
            status = given
            setImmediate(() => process.exit(status))
        }
    }
    // Whether main was called: postRun runs all the same in a program whose glue never calls
    // it (-sINVOKE_RUN=0). The glue's callMain, in the scope this file shares, is wrapped; a
    // glue whose callMain were gone would fail every test, rather than pass any.
    let called = false
    if (typeof callMain === 'function') {
        const call = callMain
        callMain = (...args) => {
            called = true
            return call(...args)
        }
    }
    // After main returned: under Asyncify a main that suspended returns early, unwound, and
    // Asyncify.currData is then set; that return is not main's end.
    Module['postRun'] = [].concat(Module['postRun'] ?? [], () => {
        if (called && (typeof Asyncify === 'undefined' || !Asyncify.currData)) {
            finished = true
        }
    })
    // The status exit_status gave is restored over any later write; otherwise a status other
    // than 0 is a failure already, and only a 0 that main never said is replaced.
    process.on('exit', () => {
        if (status !== null) {
            process.exitCode = status
            return
        }
        if (!finished && !process.exitCode) {
            process.exitCode = 1
            process.stderr.write('webcpp: main did not finish: it never ran, never returned, ' +
                'or ended after a suspension under Asyncify through a return or std::exit, ' +
                'which loses the status; end it with webcpp::test::exit_status\n')
        }
    })
}

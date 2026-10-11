#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks emscripten as a target of the build, on the fixture library browser_demo: its tests and
examples run under node, which b2's emscripten toolset runs itself, and a testing.launcher is
refused there; a program that node runs reads the host's files and standard input (-sNODERAWFS=1),
and no other program gets the flag; every program is wasm32, whatever address model is asked for; a
failure reaches the report; a program of webcpp.link is linked and never run, and fails on a symbol
nothing defines; a test of webcpp.drive runs its program through a script of node's on each of its
targets, in an own lane, a driver or a program that hangs fails it within its bound and leaves no
process behind, and one that no own lane names is refused; and a native build needs no Emscripten.
The suspension variant, jspi by default and asyncify on request, builds with the exceptions each
needs, asyncify in a directory of its own, and natively adds nothing. Every program node runs links
the test support (/webcpp//node-test), whose fixture library node_test_demo pins each case's exact
status: a main that did not finish fails, the first status given through webcpp::test::exit_status
ends the test at once and is kept, and a test past its bound is stopped; a program node runs that
links -sMODULARIZE or -sEXPORT_ES6, which node would load without running, is refused. Each case
builds a scratch superproject with browser_demo and node_test_demo, whose path holds a space, and
the emsdk linked into its .local; Emscripten's cache is the one the harness gives every b2. Run
with the names of some cases to run only those."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import harness

EMSCRIPTEN = ('toolset=emscripten',)

PASSED = re.compile(r'^\*\*passed\*\* (.*)$', re.MULTILINE)

REPORT = harness.ROOT / 'tools/report/report.py'

# The tests of browser_demo's test Jamfile, which every target builds; each target also compiles
# alone the header that builds only there: page.hpp on emscripten, native.hpp natively.
TESTS = {'alone-browser_demo', 'reads', 'catches', 'pointer', 'json', 'fails'}
EMSCRIPTEN_ALONE = 'alone-browser_demo-page'
NATIVE_ALONE = 'alone-browser_demo-native'

# What b2 says when a testing.launcher is given on emscripten.
NO_LAUNCHER = ("webcpp: b2's emscripten toolset runs a program with node itself; give no "
               'testing.launcher on emscripten')


def passed(result: subprocess.CompletedProcess) -> set[str]:
    """The tests b2 reports as passed, by name: reads for .../reads.test/.../reads.test."""
    return {path.rsplit('/', 1)[-1].removesuffix('.test') for path in PASSED.findall(result.stdout)}


def built(root: Path, name: str) -> list[Path]:
    """The files named name that b2 wrote under the scratch superproject's bin/."""
    return sorted((root / 'bin').rglob(name))


def run_lines(result: subprocess.CompletedProcess, name: str) -> list[str]:
    """The lines of b2's output (-d+2) that run the program name's JavaScript with node."""
    run = re.compile(rf'"[^"]*node" "[^"]*/{re.escape(name)}\.js"')
    return [line for line in result.stdout.splitlines() if run.search(line)]


def link_line(root: Path, result: subprocess.CompletedProcess, name: str) -> str:
    """What b2 (-d+2) linked the program name with: its command line, and the response file it
    names, when there is one."""
    output = re.compile(rf'-o "[^"]*/{re.escape(name)}\.js"')
    lines = [line for line in result.stdout.splitlines() if output.search(line)]
    assert len(lines) == 1, (name, lines, result.stdout[-4000:])
    files = [Path(file) for file in re.findall(r'@"([^"]+)"', lines[0])]
    return lines[0] + ''.join(f'\n{(root / file).read_text()}' for file in files)


def reported(root: Path, lane: str) -> subprocess.CompletedProcess:
    """What the report says of the lane, from the file <lane>.xml that b2 wrote in root."""
    return subprocess.run([sys.executable, str(REPORT), '--lane', f'{lane}={root / f"{lane}.xml"}',
                           '--out', str(root / 'report')], capture_output=True, text=True,
                          check=False)


def test_emscripten_lane_runs_under_node(root):
    result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, 'libs/browser_demo/test',
                            'libs/browser_demo/example')
    harness.expect(result, True)
    assert passed(result) == TESTS | {EMSCRIPTEN_ALONE, 'page'}, (passed(result),
                                                                result.stdout[-4000:])
    # b2's toolset runs each test's JavaScript with the node it registered, once, and the example
    # runner runs the example's with node.
    for name in ('reads', 'catches', 'pointer', 'json', 'fails'):
        assert len(run_lines(result, name)) == 1, (name, result.stdout[-4000:])
    example = re.compile(r'--launcher "node" .* -- "[^"]*/hello\.js"$')
    assert len([line for line in result.stdout.splitlines() if example.search(line)]) == 1, (
        result.stdout[-4000:])
    assert 'node "node"' not in result.stdout and '"node" "node"' not in result.stdout
    # The example read its standard input under node.
    outputs = built(root, 'hello.output')
    assert len(outputs) == 1 and outputs[0].read_text() == 'hello, node\n', outputs
    # Emscripten's cache is the harness's, never the emsdk's.
    assert any(harness.emscripten_cache().iterdir()), harness.emscripten_cache()


def test_a_launcher_is_refused_on_emscripten(root):
    # b2's emscripten toolset runs a program with node itself: a launcher would make the command
    # `node "node" x.js`, which fails, so it is refused by name before anything is built.
    result = harness.run_b2(root, *EMSCRIPTEN, 'testing.launcher=node',
                            'libs/browser_demo/test', 'libs/browser_demo/example')
    harness.expect(result, False, NO_LAUNCHER)
    assert not built(root, '*.js'), built(root, '*.js')


def test_input_file_is_read_from_the_host(root):
    # A program that node runs reads the host's files: reads opens its input file, which it would
    # read as empty without -sNODERAWFS=1. A program of webcpp.link never runs under node, and
    # does not get the flag.
    result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, 'libs/browser_demo/test//reads',
                            'libs/browser_demo/example//page')
    harness.expect(result, True)
    assert passed(result) == {'reads', 'page'}, (passed(result), result.stdout[-4000:])
    assert '-sNODERAWFS=1' in link_line(root, result, 'reads')
    assert '-sNODERAWFS=1' not in link_line(root, result, 'page')
    assert '-sENVIRONMENT=web' in link_line(root, result, 'page')


def test_programs_are_wasm32(root):
    # Browsers do not all run memory64: a program is wasm32 even when address-model=64 is asked
    # for, which b2's toolset would build with -sMEMORY64=1.
    for request in ((), ('address-model=64',)):
        result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, *request,
                                'libs/browser_demo/test//pointer')
        harness.expect(result, True)
        assert passed(result) == {'pointer'}, (request, result.stdout[-4000:])
        assert '-sMEMORY64' not in result.stdout, request
    directories = [path for path in (root / 'bin').rglob('*') if 'address-model-64' in path.name]
    assert not directories, directories


def test_suspend_variants_build_apart(root):
    # jspi, the default, compiles with WebAssembly exceptions and adds no directory; asyncify
    # composes JavaScript exceptions, which Asyncify needs (an Asyncify program built with
    # -fwasm-exceptions traps, measured with Emscripten 6.0.11), and builds in a directory of its
    # own.
    result = harness.run_b2(root, '-a', '-n', '-d+2', *EMSCRIPTEN,
                            'libs/browser_demo/test//catches')
    harness.expect(result, True)
    assert '-fwasm-exceptions' in result.stdout and 'webcpp-suspend-' not in result.stdout, (
        result.stdout[-4000:])
    result = harness.run_b2(root, '-a', '-n', '-d+2', *EMSCRIPTEN, 'webcpp-suspend=asyncify',
                            'libs/browser_demo/test//catches')
    harness.expect(result, True)
    assert '-fexceptions' in result.stdout, result.stdout[-4000:]
    assert '-fwasm-exceptions' not in result.stdout, result.stdout[-4000:]
    assert '/webcpp-suspend-asyncify/' in result.stdout, result.stdout[-4000:]


def test_a_native_build_ignores_the_variant(root):
    # The feature exists on every toolset; natively its default adds nothing.
    harness.without_emscripten(root)
    result = harness.run_b2(root, '-a', 'libs/browser_demo/test')
    harness.expect(result, True)
    assert not [path for path in (root / 'bin').rglob('*') if 'webcpp-suspend' in path.name]


NODE_TEST = 'libs/node_test_demo/test'


def exit_status(root: Path, name: str) -> tuple[int, str]:
    """The status b2 recorded for the program name, and what it printed."""
    outputs = built(root, f'{name}.output')
    assert len(outputs) == 1, (name, outputs)
    text = outputs[0].read_text()
    found = re.search(r'^EXIT STATUS: ([0-9]+)$', text, re.MULTILINE)
    assert found, (name, text)
    return int(found.group(1)), text


def test_a_test_ends_as_its_main_ends(root):
    started = time.monotonic()
    result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, NODE_TEST)
    harness.expect(result, True)
    assert passed(result) == {
        'returns_without_suspension', 'exits_zero_after_suspension_jspi',
        'exits_zero_after_suspension_asyncify', 'returns_one_after_suspension_jspi',
        'returns_zero_after_suspension_asyncify', 'never_finishes',
        'exit_in_coroutine_asyncify', 'exit_in_handler_jspi',
        'returns_zero_after_suspension_jspi', 'never_resumes_jspi', 'never_resumes_asyncify',
        'keeps_the_first_status_jspi', 'keeps_the_first_status_asyncify',
        'ends_with_a_timer_pending_jspi', 'ends_with_a_timer_pending_asyncify',
        'exits_unmarked_jspi', 'exits_unmarked_asyncify', 'bound_zero',
        'bound_too_long'}, result.stdout[-4000:]
    assert exit_status(root, 'returns_one_after_suspension_jspi')[0] == 1
    # Under JSPI a main that returns 0 after a suspension finished: the pre-js reads its end
    # after main's promise settles, never before.
    assert exit_status(root, 'returns_zero_after_suspension_jspi')[0] == 0
    status, text = exit_status(root, 'returns_zero_after_suspension_asyncify')
    assert status == 1 and 'webcpp: main did not finish' in text, text
    status, text = exit_status(root, 'never_finishes')
    assert status == 1 and 'webcpp: the test ran past its bound of 3 s' in text, text
    # A main that awaits what never comes, with nothing else alive, fails as node ends, long
    # before its bound.
    for name in ('never_resumes_jspi', 'never_resumes_asyncify'):
        status, text = exit_status(root, name)
        assert status == 1 and 'webcpp: main did not finish' in text, (name, text)
        assert 'past its bound' not in text, (name, text)
    assert exit_status(root, 'exit_in_coroutine_asyncify')[0] == 3
    assert exit_status(root, 'exit_in_handler_jspi')[0] == 3
    # The first status exit_status gives ends the test at once: neither a later exit_status(0)
    # nor a later write of process.exitCode = 0 replaces it, and a pending timer does not hold
    # it to its bound.
    for name in ('keeps_the_first_status_jspi', 'keeps_the_first_status_asyncify'):
        assert exit_status(root, name)[0] == 3, name
    for name in ('ends_with_a_timer_pending_jspi', 'ends_with_a_timer_pending_asyncify'):
        status, text = exit_status(root, name)
        assert status == 0 and 'past its bound' not in text, (name, text)
    # An unmarked std::exit after a suspension: JSPI keeps its status, Asyncify fails it.
    assert exit_status(root, 'exits_unmarked_jspi')[0] == 0
    status, text = exit_status(root, 'exits_unmarked_asyncify')
    assert status == 1 and 'webcpp: main did not finish' in text, text
    # A bound node's timers cannot hold is refused, naming it.
    for name, seconds in (('bound_zero', 0), ('bound_too_long', 2147484)):
        status, text = exit_status(root, name)
        assert status == 1 and (f'webcpp: the bound of {seconds} s is outside 1 to 2147483 s'
                                in text), (name, text)
    assert time.monotonic() - started < 300, 'a test waited for its bound'


def test_a_program_node_cannot_run_is_refused(root):
    # -sMODULARIZE and -sEXPORT_ES6 wrap a program in a factory that node never calls, so a run
    # would pass having run nothing: webcpp.run, webcpp.run-fail and webcpp.example refuse them
    # on emscripten, naming the flag; webcpp.link, for a page, takes them.
    jamfile = root / 'libs/node_test_demo/test/Jamfile'
    text = jamfile.read_text()
    for declaration, flag in (
            ('webcpp.run modular : returns.cpp : <linkflags>-sMODULARIZE=1', '-sMODULARIZE=1'),
            ('webcpp.run-fail modular : returns.cpp : <linkflags>-sEXPORT_ES6', '-sEXPORT_ES6'),
            ('webcpp.run modular : returns.cpp : <toolset>emscripten:<linkflags>-sMODULARIZE',
             '-sMODULARIZE'),
            ('webcpp.example returns.cpp : <linkflags>-sEXPORT_ES6=1', '-sEXPORT_ES6=1')):
        jamfile.write_text(f'{text}{declaration} ;\n')
        result = harness.run_b2(root, '-n', *EMSCRIPTEN, NODE_TEST)
        harness.expect(result, False, f'webcpp: {flag} makes node load the program without '
                       'running it')
    jamfile.write_text(f'{text}webcpp.link modular : returns.cpp : <linkflags>-sMODULARIZE=1 ;\n')
    result = harness.run_b2(root, *EMSCRIPTEN, f'{NODE_TEST}//modular')
    harness.expect(result, True)
    assert passed(result) == {'modular'}, result.stdout[-4000:]


def test_every_test_and_example_links_the_support(root):
    # webcpp.run, webcpp.run-fail and webcpp.example link the pre-js on emscripten; a program
    # webcpp.link links, which a browser runs, does not.
    result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, 'libs/browser_demo/test',
                            'libs/browser_demo/example')
    harness.expect(result, True)
    assert 'node-pre.js' in link_line(root, result, 'reads')
    assert 'node-pre.js' in link_line(root, result, 'hello')
    assert 'node-pre.js' not in link_line(root, result, 'page')


def test_natively_the_support_is_a_header(root):
    harness.without_emscripten(root)
    result = harness.run_b2(root, '-a', '-d+2', 'libs/browser_demo/test//reads')
    harness.expect(result, True)
    assert 'tools/node-test/include' in result.stdout and 'node-pre.js' not in result.stdout


def test_a_failure_reaches_the_report(root):
    harness.replace(root / 'libs/browser_demo/test/reads_test.cpp',
                    'BOOST_TEST_EQ(line, "hello");', 'BOOST_TEST_EQ(line, "goodbye");')
    result = harness.run_b2(root, '-a', '--dump-tests', '--out-xml=emscripten.xml', *EMSCRIPTEN,
                            'libs/browser_demo/test')
    # It fails on what it read from the host, not on an empty file.
    harness.expect(result, True, "('hello' == 'goodbye') failed")
    report = reported(root, 'emscripten')
    assert report.returncode == 1, (report.stdout, report.stderr)
    assert report.stderr.splitlines() == ['report: emscripten: browser_demo/reads: run'], (
        report.stderr)


def test_link_only_builds_and_never_runs(root):
    # page's main returns 1, and it is linked for a browser, which node refuses: it passes because
    # it links, and nothing runs it.
    result = harness.run_b2(root, '-a', '-d+2', *EMSCRIPTEN, 'libs/browser_demo/example//page')
    harness.expect(result, True)
    assert passed(result) == {'page'}, (passed(result), result.stdout[-4000:])
    assert len(built(root, 'page.js')) == 1 and len(built(root, 'page.wasm')) == 1, (
        built(root, 'page.*'))
    assert not run_lines(result, 'page'), result.stdout[-4000:]
    assert not built(root, 'page.run') and not built(root, 'page.output')
    # The program alone, for a target that needs its files, is the explicit page-program, which
    # b2 names after its target.
    result = harness.run_b2(root, '-a', *EMSCRIPTEN, 'libs/browser_demo/example//page-program')
    harness.expect(result, True)
    assert len(built(root, 'page-program.js')) == 1, built(root, 'page-program.*')
    assert len(built(root, 'page-program.wasm')) == 1, built(root, 'page-program.*')
    # Natively, the ordinary lane does not build it: it declares emscripten alone.
    result = harness.run_b2(root, '-a', 'libs/browser_demo/example')
    harness.expect(result, True)
    assert not passed(result), result.stdout[-4000:]


def test_link_only_unresolved_symbol_fails(root):
    harness.replace(root / 'libs/browser_demo/example/page.cpp', 'int main() {\n    return 1;\n}',
                    'int defined_nowhere();\n\nint main() {\n    return defined_nowhere();\n}')
    result = harness.run_b2(root, '-a', *EMSCRIPTEN, 'libs/browser_demo/example//page')
    harness.expect(result, False, 'defined_nowhere')
    assert not passed(result), result.stdout[-4000:]


def test_drive_runs_its_program_on_each_target(root):
    # The test builds driven and runs `node drive.mjs --program <program>`: the program's
    # JavaScript on emscripten, the program itself natively.
    lanes = harness.run_lanes(root, {
        'emscripten': ('-a', '-d+2', '--build-dir=bin/lane-emscripten', *EMSCRIPTEN,
                       'libs/browser_demo/test/driver//driver'),
        'native': ('-a', '-d+2', '--build-dir=bin/lane-native',
                   'libs/browser_demo/test/driver//driver'),
    })
    for name, result in lanes.items():
        harness.expect(result, True, 'drive.mjs: the program is ready')
        assert passed(result) == {'driven'}, (name, result.stdout[-4000:])
    assert re.search(r'"node" "[^"]*/drive\.mjs" "--program" "[^"]*/driven\.js"',
                     lanes['emscripten'].stdout), lanes['emscripten'].stdout[-4000:]
    # The ordinary lanes never build it: only its own lane does.
    result = harness.run_b2(root, '-a', *EMSCRIPTEN, 'libs/browser_demo/test')
    harness.expect(result, True)
    assert 'driven' not in passed(result), result.stdout[-4000:]
    # A driver that fails fails the test, as a run, in the report.
    harness.replace(root / 'libs/browser_demo/test/driver/drive.mjs',
                    "import { spawnSync } from 'node:child_process';\n",
                    "import { spawnSync } from 'node:child_process';\n\nprocess.exit(1);\n")
    lane = 'emscripten.browser_demo.driver'
    result = harness.run_b2(root, '-a', '--dump-tests', f'--out-xml={lane}.xml', *EMSCRIPTEN,
                            'libs/browser_demo/test/driver//driver')
    harness.expect(result, True)
    report = reported(root, lane)
    assert report.returncode == 1, (report.stdout, report.stderr)
    assert report.stderr.splitlines() == [f'report: {lane}: browser_demo/driven: run'], (
        report.stderr)


def leftovers(root: Path) -> list[str]:
    """The processes ps lists whose command names the scratch superproject root."""
    listed = subprocess.run(['ps', '-A', '-o', 'pid=,stat=,command='], capture_output=True,
                            text=True, check=True).stdout.splitlines()
    return [line for line in listed if str(root) in line and ' Z' not in line[:12]]


def test_a_hanging_drive_is_stopped_within_its_bound(root):
    # A driver that hangs, and a driver whose program hangs, fail the test once its bound has
    # passed, here 5 s by the requirement <webcpp-drive-timeout>, as a run failure the report
    # names, and leave no process behind: drive.py stops the driver's whole group.
    jamfile = root / 'libs/browser_demo/test/driver/Jamfile'
    harness.replace(jamfile, 'webcpp.drive driven : driven.cpp : :',
                    'webcpp.drive driven : driven.cpp : <webcpp-drive-timeout>5 :')
    driver = root / 'libs/browser_demo/test/driver/drive.mjs'
    program = root / 'libs/browser_demo/test/driver/driven.cpp'
    original = (driver.read_text(), program.read_text())
    lane = 'native.browser_demo.driver'
    for plant, toolset in (
        (lambda: harness.replace(driver, "import { spawnSync } from 'node:child_process';\n",
                                 "import { spawnSync } from 'node:child_process';\n\n"
                                 'setInterval(() => {}, 1000);\nawait new Promise(() => {});\n'),
         ()),
        (lambda: harness.replace(program, '    std::puts("ready");\n',
                                 '    for (;;) {\n        std::this_thread::sleep_for('
                                 'std::chrono::seconds(1));\n    }\n'), ()),
        (lambda: harness.replace(program, '    std::puts("ready");\n',
                                 '    for (volatile int spin = 0;; spin = spin + 1) {\n    }\n'),
         EMSCRIPTEN),
    ):
        driver.write_text(original[0])
        program.write_text(original[1].replace('#include <cstdio>\n',
                                               '#include <chrono>\n#include <cstdio>\n'
                                               '#include <thread>\n'))
        plant()
        name = 'emscripten.browser_demo.driver' if toolset else lane
        began = time.monotonic()
        result = harness.run_b2(root, '-a', '--dump-tests', f'--out-xml={name}.xml', *toolset,
                                'libs/browser_demo/test/driver//driver', timeout=300)
        took = time.monotonic() - began
        harness.expect(result, True)
        assert re.search(r'drive: webcpp\.drive driven in libs/browser_demo/test/driver/Jamfile: '
                         r'the driver of \S*/driven(\.js)? did not end within 5 s; it was stopped '
                         'with every process of its group', result.stdout), result.stdout[-4000:]
        report = reported(root, name)
        assert report.stderr.splitlines() == [f'report: {name}: browser_demo/driven: run'], (
            report.stderr)
        assert took < 200, took
        assert not leftovers(root), leftovers(root)


def test_a_drive_outside_every_lane_is_refused(root):
    result = harness.run_b2(root, '-d0', 'declared-lanes')
    harness.expect(result, True)
    assert result.stdout == ('browser_demo driver libs/browser_demo/test/driver emscripten '
                             'original\n'
                             'browser_demo driver libs/browser_demo/test/driver native '
                             'original\n'), (
        result.stdout)
    jamfile = root / 'libs/browser_demo/test/driver/Jamfile'
    text = jamfile.read_text()
    lane = 'webcpp.lane driver : driven : native emscripten ;\n'
    shown = 'webcpp.drive driven in libs/browser_demo/test/driver/Jamfile'
    for lanes, message in (
        ('', f'{shown} is in no own lane; name it in a webcpp.lane that names its targets'),
        ('webcpp.lane driver : driven : emscripten ;\n',
         f'{shown} is built for native, which no own lane that names it runs on'),
    ):
        jamfile.write_text(text.replace(lane, lanes))
        harness.expect(harness.run_b2(root, '-d0', 'declared-lanes'), False, message)
    # A Jamfile without webcpp.original cannot say how the script runs.
    jamfile.write_text(text.replace('webcpp.original node ;\n', ''))
    harness.expect(harness.run_b2(root, '-d0', 'declared-lanes'), False,
                   'webcpp.drive driven: webcpp.original must come first, in '
                   'libs/browser_demo/test/driver/Jamfile')


def test_native_build_needs_no_emsdk(root):
    # Without `using emscripten`, a native build of a library that declares emscripten builds its
    # native programs, and asks for no Emscripten.
    harness.without_emscripten(root)
    result = harness.run_b2(root, '-a', 'libs/browser_demo/test', 'libs/browser_demo/example')
    harness.expect(result, True)
    assert passed(result) == TESTS | {NATIVE_ALONE}, (passed(result), result.stdout[-4000:])
    outputs = built(root, 'hello.output')
    assert len(outputs) == 1 and outputs[0].read_text() == 'hello, node\n', outputs


def prepared(case):
    """case, run on a scratch superproject whose .local holds the emsdk."""
    def run(root):
        harness.link_emsdk(root)
        case(root)
    run.__name__ = case.__name__
    return run


CASES = [prepared(case) for case in (
    test_emscripten_lane_runs_under_node,
    test_a_launcher_is_refused_on_emscripten,
    test_input_file_is_read_from_the_host,
    test_programs_are_wasm32,
    test_suspend_variants_build_apart,
    test_a_native_build_ignores_the_variant,
    test_a_test_ends_as_its_main_ends,
    test_every_test_and_example_links_the_support,
    test_natively_the_support_is_a_header,
    test_a_program_node_cannot_run_is_refused,
    test_a_failure_reaches_the_report,
    test_link_only_builds_and_never_runs,
    test_link_only_unresolved_symbol_fails,
    test_drive_runs_its_program_on_each_target,
    test_a_hanging_drive_is_stopped_within_its_bound,
    test_a_drive_outside_every_lane_is_refused,
    test_native_build_needs_no_emsdk,
)]


if __name__ == '__main__':
    sys.exit(harness.run_cases('emscripten_test', CASES, sys.argv[1:],
                               fixtures=('browser_demo', 'node_test_demo')))

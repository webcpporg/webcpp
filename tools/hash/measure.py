#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""webcpp::hash's measured table (spec section 4.2), and the files generated from it.

    python3 tools/hash/measure.py --write [--invocations N] [--jobs N]
    python3 tools/hash/measure.py --check --programs <list>...
    python3 tools/hash/measure.py --capabilities
    python3 tools/hash/measure.py --overrides

Run from anywhere; paths in messages are relative to the superproject. Every cell of
libs/hash/doc/capabilities.json (a function on a backend; a key derivation over hmac_sha2_256
and over hmac_sha2_512) has one program, test/measure/<function>_<backend>.cpp, built on every
target of its backend at variant=release optimization=space (its size: the native executable
stripped with `strip`, or the .wasm) and at optimization=speed (its throughput, the median of
five runs per invocation, natively and on each WebAssembly target where the program ends within
BOUND seconds).

--write builds every program with b2 (the target measure-programs of test/measure/Jamfile, in
--build-dir), measures each, and writes doc/measurements.json (the data, with the machine,
compilers, runtimes, date, pins and a digest of its content), doc/measurements.adoc (its tables,
the orders and the default the owner's rule gives), include/webcpp/hash/detail/ranking.hpp (per
target and algorithm, the backends by size and by throughput), and the files generated from the
capability table alone: detail/overrides.hpp (--overrides), doc/backends.adoc (--capabilities)
and test/measure/cells.jam (the programs). `--measured FILE` takes the measurements from FILE,
in the shape of doc/measurements.json, instead of making them.

--check is the measure lane's (test/measure/Jamfile): it re-measures every program for size b2
built (the lists the lane writes, one per target), each run once, and fails, naming
`python3 tools/hash/measure.py --write`, when a program of a cell is missing on a target (the
lane built nothing), when a result differs from the committed one or from the independent value
Python computes, when the order by size of any row differs from the committed one, when a
generated file differs from what the committed data renders (a hand edit), or when the data's
digest does not match (a hand edit of the data). With `--measured`, it compares those
measurements instead, throughput included. It also runs bench/'s correctness program, which the
lists name, on every target (ruling R31): it must exit 0.

The orders follow spec 4.2 and nothing else (ruling R33). By size, the smallest program first.
By throughput, the lowest median (of the invocations' medians) first; a committed order changes
only where a backend's median is more than 10 percent below the median of the one ahead of it;
on a first measurement the medians alone order it, an exact tie keeping the capability table's
order of backends. A WebAssembly target orders by its own throughput where every backend of the
row ran within the bound, else by the native order. The native orders are those of the native
toolchain that measured them (native_toolchain in the data): a lane whose native toolchain is
another builds and checks every native program and result, and says in one line that it does not
compare the native orders (ruling R34); the WebAssembly orders, whose toolchains are pinned, are
always compared.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import datetime
import hashlib
import hmac as python_hmac
import json
import os
import platform
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WRITE = 'python3 tools/hash/measure.py --write'
TARGETS = ('native', 'wasip2', 'wasip3', 'emscripten')
OPTIMIZATIONS = ('space', 'speed')
WASM = ('wasip2', 'wasip3', 'emscripten')
# Spec 4.2: a key derivation is measured over these two hmacs.
MEASURED_HMACS = ('hmac_sha2_256', 'hmac_sha2_512')
# The library that every program names already (test/measure/Jamfile's project).
HASH_JAMFILE = '/webcpp/hash//hash'
# A WebAssembly program's throughput counts when one invocation ends within this many seconds.
BOUND = 120
# bench/'s correctness program derives 1,000,000 iterations per variant: its own bound.
BENCH_BOUND = 900
# The invocations of each program for throughput, the committed table's method.
INVOCATIONS = 5
# Spec 4.2: a committed order by throughput changes only when a median moves past this fraction.
MARGIN = 0.10

LAUNCHERS = {
    'native': [],
    'wasip2': [str(ROOT / 'tools/boost/asio-wasip2/run.sh')],
    'wasip3': [str(ROOT / 'tools/boost/asio-wasip3/run.sh')],
    'emscripten': ['node'],  # replaced by the toolset's node, which the lane's list names
}

LICENCE_SLASHES = """// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)
"""
LICENCE_HASH = '\n'.join('#' + line[2:] for line in LICENCE_SLASHES.splitlines()) + '\n'

RULES = {
    'size': 'the bytes of the program built at variant=release optimization=space: natively the '
            'executable stripped with strip, on WebAssembly the .wasm file',
    'throughput': 'the program built at variant=release optimization=speed, run with --time: one '
                  'computation to warm up, then five timed runs of the workload, each repeated '
                  '`repetitions` times; per invocation the median of its five runs, per record '
                  'the median of its invocations\' medians, with the fastest and slowest run',
    'order': 'spec 4.2: by size, the smallest program first; by throughput, the lowest median '
             'of the invocations\' medians first, a committed order changing only where a '
             'median is more than 10 percent below the median of the backend ahead of it; on a '
             'first measurement, the medians alone (an exact tie keeps the capability table\'s '
             'order of backends). A WebAssembly target orders by its own throughput where every '
             'backend of the row ran within the bound, else by the native order. The native '
             'orders hold for the native toolchain that measured them (native_toolchain); the '
             'lane compares them only on that toolchain (ruling R34).',
    'loaded': 'the larger of the two 1-minute load averages exceeds the core count',
}

LAYOUT = {
    'schema': 'This description. The version of the layout is "version"; a change of layout '
              'raises it. Written only by tools/hash/measure.py; "digest" is the SHA-256 of the '
              'file without it, which the measure lane checks.',
    'date, machine, load_average_before_after, loaded, rules.loaded': 'when and where the '
              'measurements were made; loaded says whether the machine was shared and loaded',
    'toolchains, runtimes, strip, pins, builds': 'the compiler per target, wasmtime and node, '
              'the strip of the native sizes, each backend\'s library and pin (from '
              'doc/capabilities.json), and the two builds',
    'native_toolchain': 'what the native orders were measured with: the compiler, the host\'s '
              'operating system and processor, and the strip; the lane compares the native '
              'size orders only where its own is the same (ruling R34)',
    'workloads': 'per function, what one computation does (spec 4.2)',
    'records[]': 'one per cell and target: operation (the function of doc/capabilities.json), '
                 'hmac (or null), backend, target, size_bytes, result (the hexadecimal output, '
                 'the same for every backend and target of an operation and hmac), throughput '
                 '(repetitions, invocations, runs_per_invocation, invocation_medians_ns, '
                 'median_ns, min_ns, max_ns: nanoseconds per computation) or null with '
                 'throughput_absent saying why. operation, hmac, backend and target are the keys '
                 'of doc/measurements.throughput.json\'s cases too, which the documentation joins '
                 'on them (ruling R21); constant time is doc/capabilities.json\'s (ruling R26).',
    'orders[]': 'per operation, hmac and target: by_size and by_throughput, the backends that '
                'have it there in order, and throughput_from, the target whose throughput '
                'ordered it; detail/ranking.hpp is generated from the rows of the key '
                'derivations, one per operation (hkdf_extract and hkdf_expand their own)',
    'rules': 'how sizes, throughput and orders are made',
}


class Failure(Exception):
    """A failure of the check or of a measurement, its message for the person."""


class Usage(Exception):
    """A wrong use of the command."""


@dataclass(frozen=True)
class Cell:
    """One program: a function on a backend, over an hmac or none."""

    function: str
    backend: str
    hmac: str | None
    targets: tuple[str, ...]
    library: str | None

    @property
    def id(self) -> str:
        return f'{self.function}_{self.backend}' + (f'_{self.hmac}' if self.hmac else '')

    @property
    def source(self) -> str:
        return f'{self.function}_{self.backend}.cpp'

    @property
    def key(self) -> tuple[str, str | None, str]:
        return (self.function, self.hmac, self.backend)


class Table:
    """doc/capabilities.json, read for what the measured table needs."""

    def __init__(self, data: dict) -> None:
        self.data = data
        self.backends = data['backends']
        self.backend_names = [b['name'] for b in self.backends]
        self.backend = {b['name']: b for b in self.backends}
        self.tagged = [b['name'] for b in self.backends if b['tag']]
        self.algorithms = data['algorithms']
        self.functions = [(a, f) for a in self.algorithms for f in a['functions']]
        self.function_names = [f['name'] for _, f in self.functions]

    def cells(self) -> list[Cell]:
        cells = []
        for _, function in self.functions:
            for name in self.backend_names:
                cell = function['backends'].get(name)
                if cell is None:
                    continue
                backend = self.backend[name]
                hmacs = [h for h in MEASURED_HMACS if h in (cell['hmacs'] or [])]
                library = None if backend['jamfile'] == HASH_JAMFILE else backend['jamfile']
                for hmac in hmacs or [None]:
                    cells.append(Cell(function['name'], name, hmac, tuple(
                        t for t in TARGETS if t in backend['targets']), library))
        return cells

    def kdf_rows(self) -> list[tuple[dict, dict]]:
        """The (algorithm, function) whose rows ranking.hpp holds: every function of an
        overridable algorithm that has a tag, each operation its own row (hkdf_extract and
        hkdf_expand beside hkdf), which the default of that operation reads."""
        return [(a, f) for a, f in self.functions if a['overridable'] and f.get('tag')]

    def chapter_of(self, function: str) -> str:
        return next(a['chapter'] for a, f in self.functions if f['name'] == function)

    def function(self, name: str) -> dict:
        return next(f for _, f in self.functions if f['name'] == name)


def read_json(path: Path) -> dict:
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def json_text(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + '\n'


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------------------------
# The workloads, and the values Python computes independently.


def pattern(n: int, a: int, b: int) -> bytes:
    return bytes((a * i + b) % 256 for i in range(n))


MESSAGE = pattern(1 << 20, 31, 7)
KEY = pattern(32, 13, 1)
SALT = pattern(32, 17, 3)
SECRET = pattern(32, 19, 5)
INFO = pattern(16, 23, 11)
PRK = pattern(64, 29, 13)
OUTPUT = 32
PBKDF2_ITERATIONS = 100_000
SCRYPT = (16384, 8, 1)

PYTHON_HASHES = {
    'md5_128': 'md5', 'sha1_160': 'sha1', 'sha2_224': 'sha224', 'sha2_256': 'sha256',
    'sha2_384': 'sha384', 'sha2_512': 'sha512', 'sha2_512_224': 'sha512_224',
    'sha2_512_256': 'sha512_256', 'sha3_224': 'sha3_224', 'sha3_256': 'sha3_256',
    'sha3_384': 'sha3_384', 'sha3_512': 'sha3_512', 'blake2b_512': 'blake2b',
    'blake2s_256': 'blake2s', 'ripemd_160': 'ripemd160',
}


def workload(table: Table, function: str) -> str:
    chapter = table.chapter_of(function)
    if function == 'hkdf_extract':
        return 'HKDF-Extract of a 32-byte IKM with a 32-byte salt, repeated 1,000 times'
    if function == 'hkdf_expand':
        return ('HKDF-Expand of 32 bytes from a digest-size PRK and a 16-byte info, repeated '
                '1,000 times')
    if function == 'hkdf':
        return ('HKDF of 32 bytes from a 32-byte IKM, a 32-byte salt and a 16-byte info, '
                'repeated 1,000 times')
    if function == 'pbkdf2':
        return 'PBKDF2 of 32 bytes from a 16-byte password and salt at 100,000 iterations'
    if function == 'argon2id':
        return ('Argon2id of 32 bytes from a 16-byte password and salt at libsodium\'s '
                'interactive costs (2 passes over 64 MiB)')
    if function == 'scrypt':
        return 'scrypt of 32 bytes from a 16-byte password and salt at N=16384, r=8, p=1 (16 MiB)'
    if chapter == 'macs':
        return 'the MAC of 1 MiB under a 32-byte key'
    return 'the hash of 1 MiB'


def python_value(function: str, hmac: str | None) -> str | None:
    """The result Python computes for the function, or None when it has none of its own."""
    try:
        if function in PYTHON_HASHES:
            return hashlib.new(PYTHON_HASHES[function], MESSAGE).hexdigest()
        if function in ('fnv1a_32', 'fnv1a_64'):
            bits = int(function[6:])
            prime, value = ((0x01000193, 0x811c9dc5) if bits == 32 else
                            (0x100000001b3, 0xcbf29ce484222325))
            for byte in MESSAGE:
                value = ((value ^ byte) * prime) % (1 << bits)
            return f'{value:0{bits // 4}x}'
        if function == 'shake_128':
            return hashlib.shake_128(MESSAGE).hexdigest(168)
        if function == 'shake_256':
            return hashlib.shake_256(MESSAGE).hexdigest(136)
        if function.startswith('hmac_') and function[5:] in PYTHON_HASHES:
            name = PYTHON_HASHES[function[5:]]
            return python_hmac.new(KEY, MESSAGE, lambda d=b'': hashlib.new(name, d)).hexdigest()
        if function == 'hmac':
            return python_hmac.new(KEY, MESSAGE, hashlib.sha256).hexdigest()
        if hmac is not None:
            name = PYTHON_HASHES[hmac[5:]]
            digest = hashlib.new(name).digest_size

            def mac(key: bytes, data: bytes) -> bytes:
                return python_hmac.new(key, data, lambda d=b'': hashlib.new(name, d)).digest()

            def expand(prk: bytes) -> bytes:
                out, block = b'', b''
                for i in range(1, -(-OUTPUT // digest) + 1):
                    block = mac(prk, block + INFO + bytes([i]))
                    out += block
                return out[:OUTPUT]

            if function == 'hkdf_extract':
                return mac(SALT, SECRET).hex()
            if function == 'hkdf_expand':
                return expand(PRK[:digest]).hex()
            if function == 'hkdf':
                return expand(mac(SALT, SECRET)).hex()
            if function == 'pbkdf2':
                return hashlib.pbkdf2_hmac(name, SECRET[:16], SALT[:16], PBKDF2_ITERATIONS,
                                           OUTPUT).hex()
        if function == 'scrypt':
            n, r, p = SCRYPT
            return hashlib.scrypt(SECRET[:16], salt=SALT[:16], n=n, r=r, p=p,
                                  maxmem=64 << 20, dklen=OUTPUT).hex()
    except (ValueError, AttributeError, KeyError):
        return None
    return None


# ---------------------------------------------------------------------------------------------
# Measuring.


def tool_version(command: list[str]) -> str:
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False)
        return (done.stdout or done.stderr).strip().splitlines()[0]
    except (OSError, IndexError):
        return 'unknown'


def sysctl(name: str) -> str:
    try:
        return subprocess.run(['sysctl', '-n', name], capture_output=True, text=True,
                              check=False).stdout.strip()
    except OSError:
        return ''


def machine() -> dict[str, Any]:
    memory = sysctl('hw.memsize')
    if not memory and hasattr(os, 'sysconf'):
        try:
            memory = str(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES'))
        except (ValueError, OSError):
            memory = '0'
    return {
        'cpu': sysctl('machdep.cpu.brand_string') or platform.processor() or platform.machine(),
        'cores': os.cpu_count(),
        'memory_gib': int(memory or 0) // 2**30,
        'os': f'{platform.system()} {platform.release()}',
    }


@dataclass
class Program:
    cell: Cell
    target: str
    optimization: str
    path: Path


def programs_of(table: Table, lists: list[Path], required: tuple[str, ...]
                ) -> tuple[list[Program], list[tuple[str, Path]]]:
    """The programs the lane's lists name, and bench/'s (target, path); fails naming each cell
    whose program of an optimization of required is missing on a target. A list
    measure-launcher-emscripten.txt names the command that runs a program on Emscripten, the
    node of b2's emscripten toolset."""
    cells = {c.id: c for c in table.cells()}
    found: dict[tuple[str, str, str], Program] = {}
    bench: list[tuple[str, Path]] = []
    for path in lists:
        if path.name == 'measure-launcher-emscripten.txt':
            words = path.read_text(encoding='utf-8').split(None, 1)
            if len(words) != 2 or words[0] != 'launcher':
                raise Failure(f'{relative(path)} names no launcher: b2\'s emscripten toolset '
                              'was configured without node')
            LAUNCHERS['emscripten'] = shlex.split(words[1])
            continue
        match = re.fullmatch(r'measure-programs-([a-z0-9]+)-([a-z]+)\.txt', path.name)
        if not match or match[1] not in TARGETS or match[2] not in OPTIMIZATIONS + ('bench',):
            raise Usage(f'{path}: not a list of the measure lane, '
                        'measure-programs-<target>-<space|speed|bench>.txt')
        target, optimization = match[1], match[2]
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            program = Path(line.strip())
            if not program.is_absolute():
                program = ROOT / program
            if optimization == 'bench':
                bench.append((target, program))
                continue
            stem = program.name
            for suffix in ('.wasm', '.js', '.exe'):
                stem = stem.removesuffix(suffix)
            prefix, _, name = stem.removesuffix('-program').partition('-')
            if prefix != optimization or name not in cells:
                raise Failure(f'{relative(path)} names {program.name}, which is no program of '
                              f'a cell of doc/capabilities.json: {WRITE}')
            found[(name, target, optimization)] = Program(cells[name], target, optimization,
                                                          program)
    missing = [f'{optimization}-{cell.id} on {target}' for cell in cells.values()
               for target in cell.targets for optimization in required
               if (cell.id, target, optimization) not in found]
    if missing:
        raise Failure('the measure lane built nothing for ' + ', '.join(missing)
                      + ': every cell of doc/capabilities.json has its program on every target '
                      'of its backend (a skipped program is a failure, not a missing row)')
    bench_targets = {t for t, _ in bench}
    if lists and bench_targets != set(TARGETS):
        absent = ', '.join(t for t in TARGETS if t not in bench_targets)
        raise Failure(f'the measure lane built nothing for bench/pbkdf2_sha512 on {absent}')
    return list(found.values()), bench


def size_of(program: Program, strip: str) -> int:
    if program.target == 'native':
        with tempfile.TemporaryDirectory() as scratch:
            copy_path = Path(scratch) / program.path.name
            shutil.copy2(program.path, copy_path)
            done = subprocess.run([strip, str(copy_path)], capture_output=True, text=True,
                                  check=False)
            if done.returncode != 0:
                raise Failure(f'{strip} {program.path}: {done.stderr.strip()}')
            return copy_path.stat().st_size
    wasm = program.path.with_suffix('.wasm')
    if not wasm.is_file():
        raise Failure(f'{program.path}: no {wasm.name} beside it')
    return wasm.stat().st_size


def run_program(target: str, path: Path, args: list[str], timeout: float | None
                ) -> subprocess.CompletedProcess[str] | None:
    command = LAUNCHERS[target] + [str(path), *args]
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def parse_output(program: Program, text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        word, _, rest = line.partition(' ')
        if word == 'result':
            out['result'] = rest.strip()
        elif word == 'compiler':
            out['compiler'] = rest.strip()
        elif word == 'repetitions':
            out['repetitions'] = int(rest)
        elif word == 'runs_ns':
            out['runs_ns'] = [int(x) for x in rest.split()]
    if 'result' not in out:
        raise Failure(f'{program.optimization}-{program.cell.id} on {program.target} printed '
                      f'no result:\n{text}')
    return out


def run_once(program: Program) -> dict[str, Any]:
    done = run_program(program.target, program.path, [], BOUND)
    if done is None:
        raise Failure(f'{program.optimization}-{program.cell.id} on {program.target} did not '
                      f'end within {BOUND} seconds')
    if done.returncode != 0:
        raise Failure(f'{program.optimization}-{program.cell.id} on {program.target}: exit '
                      f'{done.returncode}\n{done.stdout}{done.stderr}')
    return parse_output(program, done.stdout)


def run_timed(program: Program) -> dict[str, Any] | None:
    bound = BOUND if program.target in WASM else None
    done = run_program(program.target, program.path, ['--time'], bound)
    if done is None:
        return None
    if done.returncode != 0:
        raise Failure(f'{program.optimization}-{program.cell.id} on {program.target} --time: '
                      f'exit {done.returncode}\n{done.stdout}{done.stderr}')
    return parse_output(program, done.stdout)


def run_bench(target: str, path: Path) -> None:
    done = run_program(target, path, [], BENCH_BOUND)
    if done is None:
        raise Failure(f'bench/pbkdf2_sha512 (pbkdf2_sha512_key) on {target} did not end within '
                      f'{BENCH_BOUND} seconds')
    if done.returncode != 0:
        raise Failure(f'bench/pbkdf2_sha512 (pbkdf2_sha512_key) on {target}: exit '
                      f'{done.returncode}\n{done.stdout}{done.stderr}')


def native_toolchain(bench: list[tuple[str, Path]], strip: str) -> dict[str, str]:
    """What measures natively: the compiler, as bench/'s native program states it, the host's
    operating system and processor, and the strip, by its resolved path."""
    compiler = 'unknown'
    for target, path in bench:
        if target != 'native':
            continue
        done = run_program(target, path, ['hash2', '--runs', '1'], BENCH_BOUND)
        if done is not None and done.returncode == 0 and done.stdout.strip():
            try:
                compiler = str(json.loads(done.stdout.strip().splitlines()[-1])['compiler'])
            except (json.JSONDecodeError, KeyError):
                pass
    found = shutil.which(strip)
    return {'compiler': compiler, 'os': platform.system(), 'processor': platform.machine(),
            'strip': str(Path(found).resolve()) if found else strip}


def parallel(function: Callable[[Any], Any], items: list[Any], jobs: int) -> list[Any]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(function, items))


def measure(table: Table, programs: list[Program], bench: list[tuple[str, Path]],
            invocations: int, jobs: int, strip: str) -> dict[str, Any]:
    """Sizes and results of every program (each run once, in parallel), and, with invocations,
    the throughput of every program built for speed, invocation after invocation round-robin
    over the programs, one at a time, so that a change of load falls on all alike."""
    space = [p for p in programs if p.optimization == 'space']
    speed = [p for p in programs if p.optimization == 'speed']
    sizes = dict(zip([(p.cell.id, p.target) for p in space],
                     parallel(lambda p: size_of(p, strip), space, jobs)))
    once = dict(zip([(p.cell.id, p.target, p.optimization) for p in programs],
                    parallel(run_once, programs, jobs)))
    parallel(lambda b: run_bench(*b), bench, jobs)
    timed: dict[tuple[str, str], list[dict[str, Any] | None]] = {}
    loads = [list(os.getloadavg())]
    for _ in range(invocations):
        for p in speed:
            timed.setdefault((p.cell.id, p.target), []).append(run_timed(p))
    loads.append(list(os.getloadavg()))
    toolchains: dict[str, str] = {}
    records = []
    for p in space:
        results = {once[(p.cell.id, p.target, o)]['result'] for o in OPTIMIZATIONS
                   if (p.cell.id, p.target, o) in once}
        if len(results) != 1:
            raise Failure(f'{p.cell.id} on {p.target}: its programs for size and for throughput '
                          f'print different results, {sorted(results)}')
        record: dict[str, Any] = {
            'operation': p.cell.function, 'hmac': p.cell.hmac, 'backend': p.cell.backend,
            'target': p.target, 'size_bytes': sizes[(p.cell.id, p.target)],
            'result': results.pop(), 'throughput': None}
        runs = timed.get((p.cell.id, p.target))
        if invocations and runs is not None:
            if any(r is None for r in runs):
                record['throughput_absent'] = (f'an invocation did not end within {BOUND} '
                                               'seconds, the lane\'s bound')
            else:
                record['throughput'] = summary([r for r in runs if r is not None])
                first = runs[0]
                assert first is not None
                toolchains.setdefault(p.target, str(first.get('compiler', 'unknown')))
        elif not invocations:
            record['throughput_absent'] = 'not measured by this run'
        records.append(record)
    cores = os.cpu_count() or 1
    return {
        'date': datetime.date.today().isoformat(),
        'machine': machine(),
        'load_average_before_after': [[round(x, 2) for x in loads[0]],
                                      [round(x, 2) for x in loads[-1]]],
        'loaded': max(loads[0][0], loads[-1][0]) > cores,
        'toolchains': {t: toolchains.get(t, 'unknown') for t in TARGETS},
        'runtimes': {'wasip2': tool_version(['wasmtime', '--version']),
                     'wasip3': tool_version(['wasmtime', '--version']),
                     'emscripten': 'node ' + tool_version([LAUNCHERS['emscripten'][0],
                                                           '--version'])},
        'strip': strip,
        'native_toolchain': native_toolchain(bench, strip),
        'records': records,
    }


def summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    repetitions = int(runs[0]['repetitions'])
    per_run = [[t / repetitions for t in r['runs_ns']] for r in runs]
    medians = [statistics.median(r) for r in per_run]
    every = [t for r in per_run for t in r]
    return {'repetitions': repetitions, 'invocations': len(runs),
            'runs_per_invocation': len(per_run[0]),
            'invocation_medians_ns': [round(m, 1) for m in medians],
            'median_ns': round(statistics.median(medians), 1),
            'min_ns': round(min(every), 1), 'max_ns': round(max(every), 1)}


# ---------------------------------------------------------------------------------------------
# The orders.


def ordered(values: dict[str, float], previous: list[str] | None, base: list[str],
            margin: float) -> list[str]:
    """The backends of values (each a median, or a size) in order, the lowest first (spec 4.2).
    Without a previous order, the values alone order them, an exact tie keeping base's order.
    With one, the previous order stands but where a backend's value is more than margin below
    the value of the one ahead of it: it moves ahead, until no such pair is left."""
    if not previous:
        return sorted((b for b in base if b in values), key=lambda b: values[b])
    start = [b for b in previous if b in values]
    order = start + sorted((b for b in base if b in values and b not in start),
                           key=lambda b: values[b])

    def beats(b: str, a: str) -> bool:
        return values[b] * (1 + margin) < values[a]

    moved = True
    while moved:
        moved = False
        for i in range(len(order) - 1):
            if beats(order[i + 1], order[i]):
                order[i], order[i + 1] = order[i + 1], order[i]
                moved = True
    return order


def orders_of(table: Table, records: list[dict], previous: list[dict] | None) -> list[dict]:
    before = {(o['operation'], o['hmac'], o['target']): o for o in previous or []}
    rows: dict[tuple[str, str | None], dict[str, dict]] = {}
    for r in records:
        rows.setdefault((r['operation'], r['hmac']), {}).setdefault(r['target'], {})[
            r['backend']] = r
    base = table.backend_names
    out = []
    for function in table.function_names:
        for hmac in [None, *MEASURED_HMACS]:
            per_target = rows.get((function, hmac))
            if not per_target:
                continue
            for target in TARGETS:
                cells = per_target.get(target)
                if not cells:
                    continue
                old = before.get((function, hmac, target), {})
                sizes = {b: float(r['size_bytes']) for b, r in cells.items()}
                by_size = ordered(sizes, old.get('by_size'), base, 0.0)
                source = target
                speeds = {b: r['throughput'] for b, r in cells.items()}
                if any(s is None for s in speeds.values()):
                    source = 'native'
                    native = per_target.get('native', {})
                    speeds = {b: native[b]['throughput'] for b in cells if b in native}
                if speeds and all(s is not None for s in speeds.values()):
                    values = {b: float(s['median_ns']) for b, s in speeds.items()}
                    by_throughput = ordered(values, old.get('by_throughput'), base, MARGIN)
                    by_throughput += [b for b in by_size if b not in by_throughput]
                else:
                    by_throughput, source = by_size, 'none: ordered by size'
                out.append({'operation': function, 'hmac': hmac, 'target': target,
                            'by_size': by_size, 'by_throughput': by_throughput,
                            'throughput_from': source})
    return out


# ---------------------------------------------------------------------------------------------
# The data file.


def record_order(table: Table) -> Callable[[dict[str, Any]], tuple[int, ...]]:
    functions = {f: i for i, f in enumerate(table.function_names)}
    backends = {b: i for i, b in enumerate(table.backend_names)}
    hmacs = {None: 0, **{h: i + 1 for i, h in enumerate(MEASURED_HMACS)}}
    targets = {t: i for i, t in enumerate(TARGETS)}
    return lambda r: (functions[r['operation']], hmacs[r['hmac']], backends[r['backend']],
                      targets[r['target']])


def digest_of(data: dict) -> str:
    body = {k: v for k, v in data.items() if k != 'digest'}
    return 'sha256:' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def data_file(table: Table, measured: dict, previous: dict | None) -> dict:
    records = sorted(copy.deepcopy(measured['records']), key=record_order(table))
    for r in records:
        r.setdefault('throughput_absent', None)
        if r['throughput'] is not None:
            r['throughput_absent'] = None
    functions = sorted({r['operation'] for r in records}, key=table.function_names.index)
    data = {
        'about': 'webcpp::hash\'s measured table (spec section 4.2): the size of one program per '
                 'cell of doc/capabilities.json on each target, and its throughput, which '
                 'detail/ranking.hpp orders the backends by. Written by tools/hash/measure.py '
                 '--write; the documentation renders from it (ruling R21).',
        'version': 1,
        'layout': LAYOUT,
        'date': measured['date'],
        'machine': measured['machine'],
        'load_average_before_after': measured['load_average_before_after'],
        'loaded': measured['loaded'],
        'toolchains': measured['toolchains'],
        'runtimes': measured['runtimes'],
        'strip': measured['strip'],
        'native_toolchain': measured.get('native_toolchain', {}),
        'pins': {b['name']: b['library'] for b in table.backends},
        'builds': {'size': 'variant=release optimization=space',
                   'throughput': 'variant=release optimization=speed'},
        'workloads': {f: workload(table, f) for f in functions},
        'rules': RULES,
        'records': records,
        'orders': orders_of(table, records, previous['orders'] if previous else None),
    }
    data['digest'] = digest_of(data)
    return data


# ---------------------------------------------------------------------------------------------
# Rendering.


def tag(table: Table, backend: str) -> str:
    return table.backend[backend]['tag']


def full_order(table: Table, order: list[str]) -> list[str]:
    """An order of ranking.hpp: the row's backends with a tag, then every other backend with a
    tag in the table's order, so that the walk of first_serving always reaches one that serves
    (ruling R23)."""
    named = [b for b in order if table.backend[b]['tag']]
    return named + [b for b in table.tagged if b not in named]


def backend_list(table: Table, order: list[str], indent: int) -> str:
    names = ', '.join(tag(table, b) for b in full_order(table, order))
    return f'backend_list<{names}>;'


def using(name: str, value: str) -> str:
    """`using <name> = <value>` in a class, as clang-format breaks it at 100 columns."""
    line = f'    using {name} = {value}'
    return line if len(line) <= 100 else f'    using {name} =\n        {value}'


def render_ranking(table: Table, data: dict) -> str:
    orders = {(o['operation'], o['hmac'], o['target']): o for o in data['orders']}
    portable = ', '.join(table.backend[b]['tag'] for b in table.tagged
                         if table.backend[b]['portable'])
    lines = [LICENCE_SLASHES.rstrip('\n'), '',
             '// Generated by tools/hash/measure.py --write from doc/measurements.json: do not '
             'edit. Per target',
             '// and key derivation, the backends ordered by their programs\' size and by '
             'their throughput',
             '// (spec section 4.2); the measure lane fails when this file differs from what '
             'the data renders.', '',
             '#ifndef WEBCPP_HASH_DETAIL_RANKING_HPP',
             '#define WEBCPP_HASH_DETAIL_RANKING_HPP', '',
             '#include <webcpp/hash/config.hpp>',
             '#include <webcpp/hash/hmac.hpp>', '',
             'namespace webcpp::hash::detail {', '',
             '/**', ' An ordered list of backends, the first preferred.', '',
             ' @tparam B The backends, tags of `backends`.', '*/',
             'template <class... B>', 'struct backend_list {};', '',
             '/**',
             ' The backends of the portable profile, in its order: those present on every '
             'target (spec 4.1).',
             '*/',
             f'using portable_order = backend_list<{portable}>;', '']
    conditions = {'wasip2': '#ifdef WEBCPP_TARGET_WASIP2',
                  'wasip3': '#elif defined(WEBCPP_TARGET_WASIP3)',
                  'emscripten': '#elif defined(WEBCPP_TARGET_EMSCRIPTEN)',
                  'native': '#else  // native'}
    for target in ('wasip2', 'wasip3', 'emscripten', 'native'):
        lines += [conditions[target], '']
        lines += ['/**',
                  f' The measured orders of the backends of a key derivation on {target} '
                  '(spec 4.2): `by_size`, the',
                  ' smallest program first, and `by_throughput`, the fastest first. This '
                  'primary template is an',
                  ' algorithm the table does not measure: the table\'s order of backends.', '',
                  ' @tparam Algorithm The algorithm\'s tag, as `kdfs::hkdf`. @tparam Hmac The '
                  'hmac of a key',
                  ' derivation, or `void`.', '*/',
                  'template <class Algorithm, class Hmac>', 'struct ranking {',
                  '    /** The smallest program first. */',
                  using('by_size', backend_list(table, [], 4)),
                  '    /** The fastest first. */',
                  using('by_throughput', backend_list(table, [], 4)),
                  '};', '']
        for _, function in table.kdf_rows():
            name = function['name']
            hmacs = [h for h in MEASURED_HMACS if (name, h, target) in orders]
            if not hmacs and (name, None, target) in orders:
                hmacs = [None]
            for i, hmac in enumerate(hmacs):
                order = orders[(name, hmac, target)]
                spec_tag = function['tag']
                if i == 0:
                    what = (f'over {hmac}, and over every hmac the table does not measure'
                            if hmac else 'which takes no hmac')
                    head = ['template <class Hmac>', f'struct ranking<{spec_tag}, Hmac> {{']
                else:
                    what = f'over {hmac}'
                    head = ['template <>', f'struct ranking<{spec_tag}, {hmac}> {{']
                lines += ['/**',
                          f' {name} on {target}, {what}: by size '
                          f'{", ".join(order["by_size"])}; by throughput '
                          f'{", ".join(order["by_throughput"])} (measured on '
                          f'{order["throughput_from"]}).',
                          '*/'] + head + [
                          '    /** The smallest program first. */',
                          using('by_size', backend_list(table, order['by_size'], 4)),
                          '    /** The fastest first. */',
                          using('by_throughput', backend_list(table, order['by_throughput'], 4)),
                          '};', '']
    lines += ['#endif', '', '}  // namespace webcpp::hash::detail', '',
              '#endif  // WEBCPP_HASH_DETAIL_RANKING_HPP', '']
    return wrap_comments('\n'.join(lines))


def wrap_comments(text: str) -> str:
    """Wraps the lines of Doc Comments (one leading space) at 100 columns."""
    out = []
    for line in text.split('\n'):
        if line.startswith(' ') and not line.startswith('  ') and len(line) > 100:
            words, current = line.split(' ')[1:], ''
            for word in words:
                if current and len(current) + 1 + len(word) > 99:
                    out.append(' ' + current)
                    current = word
                else:
                    current = f'{current} {word}' if current else word
            out.append(' ' + current)
        else:
            out.append(line)
    return '\n'.join(out)


def render_overrides(table: Table) -> str:
    lines = [LICENCE_SLASHES.rstrip('\n'), '',
             '// The per-algorithm overrides of the default backend (spec section 4.1), one '
             'block per overridable',
             '// algorithm of doc/capabilities.json and one define per backend of it that has '
             'a tag:',
             '// WEBCPP_HASH_DEFAULT_BACKEND_<ALGORITHM>_<NAME> names the backend of every '
             'function of the',
             '// algorithm, whatever the profile. Two overrides of one algorithm, and '
             'OpenSSL\'s on Emscripten,',
             '// are an #error. An override names its backend even where the backend lacks the '
             'function over',
             '// the hmac used: the call then stops with that backend\'s refusal (spec 3.3); '
             'and when the',
             '// program does not link it, hkdf.hpp and pbkdf2.hpp include its header, which '
             'stops with its',
             '// "needs" message (spec 5.7). Generated by tools/hash/measure.py --overrides '
             'from',
             '// doc/capabilities.json: do not edit; test/overrides_list_test.cpp checks it '
             'against the table',
             '// too. kdf.hpp includes it, the one reader of override_choice, so the '
             'overrides\' refusals come',
             '// with every key derivation header.', '',
             '#ifndef WEBCPP_HASH_DETAIL_OVERRIDES_HPP', '#define WEBCPP_HASH_DETAIL_OVERRIDES_HPP',
             '', '#include <webcpp/hash/config.hpp>', '',
             '/** The spelling of `x` as a string literal, unexpanded. @param x The tokens. */',
             '#define WEBCPP_HASH_DETAIL_OVERRIDE_STRING_I(x) #x',
             '/** The spelling of `x` as a string literal, once `x` is expanded. @param x The '
             'macro. */',
             '#define WEBCPP_HASH_DETAIL_OVERRIDE_STRING(x) '
             'WEBCPP_HASH_DETAIL_OVERRIDE_STRING_I(x)', '',
             'namespace webcpp::hash::detail {', '', '/**',
             ' The backend an override names for `Algorithm`, `void` without one.', '',
             ' @tparam Algorithm A tag of `kdfs`, the algorithm (not one of its steps).', '*/',
             'template <class Algorithm>', 'struct override_choice {',
             '    /** No override. */', '    using type = void;', '};', '']
    backends = [b for b in table.backends if b['tag']]
    for algorithm in table.algorithms:
        if not algorithm['overridable']:
            continue
        macro = algorithm['macro']
        prefix = f'WEBCPP_HASH_DEFAULT_BACKEND_{macro}_'
        names = ', '.join(f['name'] for f in algorithm['functions'])
        lines += [f'// {macro}: {names}.', '// clang-format off']
        for i, a in enumerate(backends):
            for b in backends[i + 1:]:
                lines += [f'#if defined({prefix}{a["macro"]}) && defined({prefix}{b["macro"]})',
                          f'#error "webcpp::hash: {prefix}{a["macro"]} and {prefix}{b["macro"]} '
                          'are both defined. Keep one."', '#endif']
        for b in backends:
            if 'emscripten' not in b['targets']:
                lines += [f'#if defined(WEBCPP_TARGET_EMSCRIPTEN) && defined({prefix}{b["macro"]})',
                          f'#error "webcpp::hash: {prefix}{b["macro"]} selects {library_name(b)}, '
                          'which is not built for Emscripten. Remove that define."', '#endif']
        lines.append('// clang-format on')
        override = f'WEBCPP_HASH_DETAIL_OVERRIDE_{macro}'
        for i, b in enumerate(backends):
            lines.append(f'#ifdef {prefix}{b["macro"]}' if i == 0
                         else f'#elif defined({prefix}{b["macro"]})')
            lines.append(f'#define {override} {b["name"]}')
            if b['name'] != 'hash2':
                lines.append(f'#define WEBCPP_HASH_DETAIL_OVERRIDES_{b["macro"]}')
        tag_name = algorithm['tag']
        lowered = macro.lower()
        lines += ['#endif', f'#ifdef {override}',
                  f'/** The backend the override of {macro} names. */', 'template <>',
                  f'struct override_choice<{tag_name}> {{', '    /** The named backend. */',
                  f'    using type = backends::{override};', '};', '#ifdef _MSC_VER',
                  f'#pragma detect_mismatch("webcpp_hash_default_backend_{lowered}", \\',
                  f'                        WEBCPP_HASH_DETAIL_OVERRIDE_STRING({override}))',
                  '#endif', '#elif defined(_MSC_VER)',
                  f'#pragma detect_mismatch("webcpp_hash_default_backend_{lowered}", "none")',
                  '#endif', '']
    lines += ['}  // namespace webcpp::hash::detail', '',
              '#endif  // WEBCPP_HASH_DETAIL_OVERRIDES_HPP', '']
    return '\n'.join(lines)


def library_name(backend: dict) -> str:
    return 'OpenSSL' if backend['name'] == 'openssl' else str(backend['name'])


def render_cells(table: Table) -> str:
    lines = [LICENCE_HASH.rstrip('\n'), '',
             '# Generated by tools/hash/measure.py --write from doc/capabilities.json: do',
             '# not edit. One program per cell, a function on a backend (a key derivation',
             '# over each hmac of spec 4.2), as test/measure/Jamfile\'s measure-cell',
             '# declares it: <name> : <source> : <library> : <hmac> : <targets>.', '']
    for cell in table.cells():
        lines += [f'measure-cell {cell.id} : {cell.source}',
                  f'  : {cell.library or ""} : {cell.hmac or ""} : {" ".join(cell.targets)} ;'
                  .replace(':  :', ': :').replace(':  :', ': :')]
    return '\n'.join(lines) + '\n'


def adoc_header(title: str, anchor: str, source: str) -> list[str]:
    return [LICENCE_SLASHES.rstrip('\n'), '',
            f'// Generated by tools/hash/measure.py from {source}: do not edit.', '',
            f'[#{anchor}]', f'== {title}', '']


def render_backends(table: Table) -> str:
    """The capability table as the documentation shows it (ruling R13): per chapter, each
    function on each backend, its hmacs and its constant time; per function, the targets each
    backend has it on."""
    lines = adoc_header('Backends', 'hash-backends', 'doc/capabilities.json')
    lines += ['Which backend implements each function, over which hmacs, on which targets, and '
              'what upstream', 'states about its constant time. The backends:', '',
              '[cols="1,3,1,2,3",options="header"]', '|===',
              '| Backend | Library | Licence | Jamfile | Targets']
    for b in table.backends:
        lines += ['', f'| {b["name"]}', f'| {b["library"]}', f'| {b["licence"]}',
                  f'| `{b["jamfile"]}`', f'| {", ".join(b["targets"])}']
    lines += ['|===', '']
    chapters: dict[str, list[dict]] = {}
    for algorithm in table.algorithms:
        chapters.setdefault(algorithm['chapter'], []).append(algorithm)
    for chapter, algorithms in chapters.items():
        lines += [f'=== {chapter.replace("_", " ").capitalize()}', '',
                  '[cols="2,1,3,1,4",options="header"]', '|===',
                  '| Function | Backend | Hmacs | Constant time | Targets']
        for algorithm in algorithms:
            for function in algorithm['functions']:
                for name in table.backend_names:
                    c = function['backends'].get(name)
                    if c is None:
                        continue
                    hmacs = ', '.join(c['hmacs']) if c['hmacs'] else '-'
                    targets = ', '.join(table.backend[name]['targets'])
                    lines += ['', f'| {function["name"]}', f'| {name}', f'| {hmacs}',
                              f'| {c["constant_time"]["value"]}', f'| {targets}']
        lines += ['|===', '']
    lines += ['=== Constant time', '', 'What each backend\'s upstream states, and where:', '']
    seen = set()
    for _, function in table.functions:
        for name, c in function['backends'].items():
            key = (name, c['constant_time']['value'], c['constant_time']['source'])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'* {name}: {c["constant_time"]["value"]}. '
                         f'{c["constant_time"]["source"]}')
    return '\n'.join(lines) + '\n'


def fmt_time(ns: float) -> str:
    if ns >= 1e6:
        return f'{ns / 1e6:.2f} ms'
    if ns >= 1e3:
        return f'{ns / 1e3:.2f} µs'
    return f'{ns:.0f} ns'


def fmt_speed(table: Table, operation: str, t: dict) -> str:
    if table.chapter_of(operation) in ('digests', 'macs', 'non-cryptographic'):
        def rate(ns: float) -> str:
            return f'{1e9 / ns:.0f}'
        return f'{rate(t["median_ns"])} MiB/s ({rate(t["max_ns"])} to {rate(t["min_ns"])})'
    return (f'{fmt_time(t["median_ns"])} ({fmt_time(t["min_ns"])} to '
            f'{fmt_time(t["max_ns"])})')


def defaults_of(table: Table, data: dict) -> list[tuple]:
    """The default the owner's rule gives (spec 4.1's auto: natively the fastest, on
    WebAssembly the smallest), per target and key derivation operation, every backend linked:
    the first of the operation's own order that has it."""
    sizes = {(r['operation'], r['hmac'], r['backend'], r['target']): r['size_bytes']
             for r in data['records']}
    orders = {(o['operation'], o['hmac'], o['target']): o for o in data['orders']}
    out = []
    for _, function in table.kdf_rows():
        name = function['name']
        for hmac in [None, *MEASURED_HMACS]:
            for target in TARGETS:
                order = orders.get((name, hmac, target))
                if order is None:
                    continue
                chosen = (order['by_size'] if target in WASM else order['by_throughput'])[0]
                smallest = order['by_size'][0]
                out.append((name, hmac, target, chosen, sizes[(name, hmac, chosen, target)],
                            smallest, sizes[(name, hmac, smallest, target)]))
    return out


def render_measurements(table: Table, data: dict) -> str:
    m = data['machine']
    lines = adoc_header('Measured size and throughput', 'hash-measurements',
                        'doc/measurements.json')
    lines += ['What each backend costs a program on each target, in bytes and in time, as '
              'webcpp measured it',
              '(spec section 4.2). The size of a backend is what matters on WebAssembly, where '
              'every byte is',
              'downloaded; its throughput is what matters natively. `detail/ranking.hpp`, '
              'generated from the',
              'same data, orders the backends of each key derivation by both, and the default '
              'backend follows it.', '',
              f'Measured on {data["date"]} on {m["cpu"]}, {m["cores"]} cores, '
              f'{m["memory_gib"]} GiB, {m["os"]};',
              f'WebAssembly under {data["runtimes"]["wasip2"]} (wasip2, wasip3) and '
              f'{data["runtimes"]["emscripten"]} (Emscripten).',
              'Compilers: ' + '; '.join(f'{t}: {c}' for t, c in data['toolchains'].items())
              + '.', '']
    native = data.get('native_toolchain') or {}
    if native:
        lines += [f'The native rows hold for {native["compiler"]} on {native["os"]} '
                  f'{native["processor"]}, stripped with {Path(native["strip"]).name}; another',
                  'native toolchain gives other native sizes and times.', '']
    if data['loaded']:
        load = data['load_average_before_after']
        lines += ['WARNING: the machine was shared and loaded while this was measured (many '
                  'builds ran at once;',
                  '1, 5 and 15 minute load averages '
                  + '/'.join(f'{x:.0f}' for x in load[0]) + ' before and '
                  + '/'.join(f'{x:.0f}' for x in load[1]) + f' after, on {m["cores"]} cores).',
                  'Every time is a median with its spread; read the spread, not a single '
                  'figure. Sizes do not',
                  'depend on the load.', '']
    lines += [f'Sizes: {RULES["size"]}. Throughput: {RULES["throughput"]}. Orders: '
              f'{RULES["order"]}', '']
    by_cell: dict[tuple, dict[str, dict]] = {}
    for r in data['records']:
        by_cell.setdefault((r['operation'], r['hmac'], r['backend']), {})[r['target']] = r
    lines += ['=== Size of a program, in bytes', '',
              '[cols="3,2,1,1,1,1,1",options="header"]', '|===',
              '| Function | Hmac | Backend | native | wasip2 | wasip3 | emscripten']
    for (operation, hmac, backend), targets in by_cell.items():
        lines += ['', f'| {operation}', f'| {hmac or "-"}', f'| {backend}']
        lines += [f'| {targets[t]["size_bytes"]}' if t in targets else '| -' for t in TARGETS]
    lines += ['|===', '', '=== Throughput', '',
              'A hash or MAC in MiB per second over 1 MiB, a key derivation in time per '
              'derivation: the median, then',
              'the range of its runs, the lower figure first. Per function, the workload:', '']
    lines += [f'* {f}: {w}.' for f, w in data['workloads'].items()]
    lines += ['', '[cols="3,2,1,3,3,3,3",options="header"]', '|===',
              '| Function | Hmac | Backend | native | wasip2 | wasip3 | emscripten']
    for (operation, hmac, backend), targets in by_cell.items():
        lines += ['', f'| {operation}', f'| {hmac or "-"}', f'| {backend}']
        for t in TARGETS:
            r = targets.get(t)
            if r is None:
                lines.append('| -')
            elif r['throughput'] is None:
                lines.append(f'| not measured: {r["throughput_absent"]}')
            else:
                lines.append(f'| {fmt_speed(table, operation, r["throughput"])}')
    lines += ['|===', '', '=== The orders of the key derivations', '',
              'The rows `detail/ranking.hpp` holds, one per operation: the default of '
              '`hkdf_extract`, `hkdf_expand` and `hkdf` each reads its own (spec 4.1).', '',
              '[cols="2,2,1,3,3,1",options="header"]', '|===',
              '| Function | Hmac | Target | By size | By throughput | Throughput of']
    kdf_names = {f['name'] for _, f in table.kdf_rows()}
    for o in data['orders']:
        if o['operation'] not in kdf_names:
            continue
        lines += ['', f'| {o["operation"]}', f'| {o["hmac"] or "-"}', f'| {o["target"]}',
                  f'| {", ".join(o["by_size"])}', f'| {", ".join(o["by_throughput"])}',
                  f'| {o["throughput_from"]}']
    lines += ['|===', '', '=== The default of each key derivation', '',
              'The owner\'s rule (spec 4.1, the profile `auto`): natively the fastest backend, '
              'on WebAssembly the',
              'smallest, among those the program links. With every backend linked, the default '
              'and the size of',
              'its program, beside the smallest program of the function on that target:', '',
              '[cols="2,2,1,1,1,1,1",options="header"]', '|===',
              '| Function | Hmac | Target | Default | Its size | Smallest | Its size']
    for name, hmac, target, chosen, size, smallest, small in defaults_of(table, data):
        lines += ['', f'| {name}', f'| {hmac or "-"}', f'| {target}', f'| {chosen}',
                  f'| {size}', f'| {smallest}', f'| {small}']
    lines += ['|===', '']
    return '\n'.join(lines)


# ---------------------------------------------------------------------------------------------
# The modes.


class Library:
    def __init__(self, path: Path) -> None:
        self.path = path
        capabilities = path / 'doc/capabilities.json'
        if not capabilities.is_file():
            raise Usage(f'{capabilities}: no doc/capabilities.json, the capability table')
        self.table = Table(read_json(capabilities))
        self.data_path = path / 'doc/measurements.json'

    def outputs(self) -> dict[str, Path]:
        return {
            'measurements.adoc': self.path / 'doc/measurements.adoc',
            'ranking': self.path / 'include/webcpp/hash/detail/ranking.hpp',
            'overrides': self.path / 'include/webcpp/hash/detail/overrides.hpp',
            'backends': self.path / 'doc/backends.adoc',
            'cells': self.path / 'test/measure/cells.jam',
        }

    def table_only(self) -> dict[str, str]:
        return {'overrides': render_overrides(self.table),
                'backends': render_backends(self.table),
                'cells': render_cells(self.table)}

    def rendered(self, data: dict) -> dict[str, str]:
        return {'measurements.adoc': render_measurements(self.table, data),
                'ranking': render_ranking(self.table, data), **self.table_only()}

    def committed(self) -> dict | None:
        return read_json(self.data_path) if self.data_path.is_file() else None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def b2_build(library: Library, build_dir: Path, jobs: int) -> list[Path]:
    """Builds every program with b2 and returns the lists of programs this build wrote, which
    the Jamfile's manifest names (-sWEBCPP_HASH_MEASURE_MANIFEST)."""
    config = ROOT / '.local/user-config.jam'
    build_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_dir / 'measure-manifest.txt'
    if manifest.exists():
        manifest.unlink()
    command = ['b2', f'-j{jobs}', f'--build-dir={build_dir}',
               f'-sWEBCPP_HASH_MEASURE_MANIFEST={manifest}']
    if config.is_file():
        command.append(f'--user-config={config}')
    command.append(f'{relative(library.path)}/test/measure//measure-programs')
    environ = {k: v for k, v in os.environ.items()
               if k not in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH')}
    print('measure: ' + ' '.join(command), flush=True)
    done = subprocess.run(command, cwd=ROOT, env=environ, check=False)
    if done.returncode != 0:
        raise Failure(f'b2 exited with {done.returncode}')
    if not manifest.is_file():
        raise Failure(f'b2 wrote no {manifest}: test/measure/Jamfile\'s measure-programs names it')
    return [path if path.is_absolute() else ROOT / path
            for path in (Path(line) for line in manifest.read_text(encoding='utf-8').split('\n')
                         if line.strip())]


def mode_write(library: Library, args: argparse.Namespace) -> None:
    table = library.table
    write_text(library.outputs()['cells'], render_cells(table))
    if args.measured:
        measured = read_json(Path(args.measured))
    else:
        lists = b2_build(library, Path(args.build_dir).resolve(), args.jobs)
        programs, bench = programs_of(table, lists, OPTIMIZATIONS)
        measured = measure(table, programs, bench, args.invocations, args.jobs, args.strip)
    check_coverage(table, measured['records'], 'the measurements')
    check_results(table, measured['records'], None)
    data = data_file(table, measured, library.committed())
    write_text(library.data_path, json_text(data))
    for name, text in library.rendered(data).items():
        write_text(library.outputs()[name], text)
    print(f'measure: wrote {relative(library.data_path)} and the files generated from it')


def check_coverage(table: Table, records: list[dict], what: str) -> None:
    have = {(r['operation'], r['hmac'], r['backend'], r['target']) for r in records}
    want = {(c.function, c.hmac, c.backend, t) for c in table.cells() for t in c.targets}
    missing = sorted(want - have, key=str)
    extra = sorted(have - want, key=str)
    if missing or extra:
        names = [f'{o}{"/" + h if h else ""} on {b}, {t}' for o, h, b, t in missing]
        others = [f'{o}{"/" + h if h else ""} on {b}, {t}' for o, h, b, t in extra]
        raise Failure(f'{what} do not cover doc/capabilities.json\'s cells: missing '
                      f'{", ".join(names) or "none"}; not in the table '
                      f'{", ".join(others) or "none"}: {WRITE}')


def check_results(table: Table, records: list[dict], committed: dict | None) -> None:
    """Every record of an operation and hmac prints one result, Python's where it has one, and
    the committed one."""
    before = {(r['operation'], r['hmac'], r['backend'], r['target']): r['result']
              for r in (committed or {}).get('records', [])}
    by_row: dict[tuple, set[str]] = {}
    for r in records:
        by_row.setdefault((r['operation'], r['hmac']), set()).add(r['result'])
        old = before.get((r['operation'], r['hmac'], r['backend'], r['target']))
        if committed and old is not None and old != r['result']:
            raise Failure(f'{r["operation"]} over {r["hmac"]} on {r["backend"]}, {r["target"]}: '
                          f'the result {r["result"]} is not the committed {old}')
    for (operation, hmac), results in by_row.items():
        if len(results) != 1:
            raise Failure(f'{operation} over {hmac}: its backends and targets disagree, '
                          f'{sorted(results)}')
        expected = python_value(operation, hmac)
        if expected is not None and expected not in results:
            raise Failure(f'{operation} over {hmac}: the result {results.pop()} is not Python\'s '
                          f'{expected}')


def describe(toolchain: dict[str, str]) -> str:
    """A native toolchain, as a message names it."""
    if not toolchain:
        return 'an unrecorded toolchain'
    return (f'{toolchain.get("compiler")} on {toolchain.get("os")} {toolchain.get("processor")} '
            f'(strip {toolchain.get("strip")})')


def mode_check(library: Library, args: argparse.Namespace) -> None:
    table = library.table
    committed = library.committed()
    problems = []
    if committed is None:
        raise Failure(f'{relative(library.data_path)} does not exist: {WRITE}')
    if committed.get('digest') != digest_of(committed):
        problems.append(f'{relative(library.data_path)} was edited by hand (its digest does not '
                        f'match): only {WRITE} writes it')
    for name, text in library.rendered(committed).items():
        path = library.outputs()[name]
        if not path.is_file() or path.read_text(encoding='utf-8') != text:
            problems.append(f'{relative(path)} is not what doc/measurements.json and '
                            f'doc/capabilities.json render (edited by hand, or stale): {WRITE}')
    if problems:
        raise Failure('\n'.join(problems))
    check_coverage(table, committed['records'], relative(library.data_path))
    if args.measured:
        measured = read_json(Path(args.measured))
    else:
        programs, bench = programs_of(table, [Path(p) for p in args.programs], ('space',))
        measured = measure(table, programs, bench, 0, args.jobs, args.strip)
    check_coverage(table, measured['records'], 'the new measurements')
    check_results(table, measured['records'], committed)
    with_throughput = all(r['throughput'] is not None for r in measured['records'])
    if not with_throughput:
        old = {(r['operation'], r['hmac'], r['backend'], r['target']): r
               for r in committed['records']}
        for r in measured['records']:
            r['throughput'] = old[(r['operation'], r['hmac'], r['backend'], r['target'])][
                'throughput']
    again = orders_of(table, measured['records'], committed['orders'])
    before = {(o['operation'], o['hmac'], o['target']): o for o in committed['orders']}
    ours = measured.get('native_toolchain') or {}
    theirs = committed.get('native_toolchain') or {}
    native = ours == theirs
    if not native:
        print('measure: the native orders were measured with '
              f'{describe(theirs)} and are not compared with {describe(ours)} (ruling R34); '
              'every native program and result is checked', flush=True)
    changes = []
    for o in again:
        if o['target'] == 'native' and not native:
            continue
        old = before.get((o['operation'], o['hmac'], o['target']))
        for key, what in (('by_size', 'by size'), ('by_throughput', 'by throughput')):
            if old is None or old[key] != o[key]:
                changes.append(f'{o["operation"]} over {o["hmac"]} on {o["target"]}: {what} '
                               f'{", ".join(o[key])}, committed '
                               f'{", ".join(old[key]) if old else "nothing"}')
    if changes:
        raise Failure('the measured order changed:\n  ' + '\n  '.join(changes)
                      + f'\nmeasure again and commit the new table: {WRITE}')
    count = len(measured['records'])
    print(f'measure: {count} cells on their targets agree with {relative(library.data_path)}'
          + ('' if with_throughput else ' (sizes and results; throughput is measured by --write)'))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description='webcpp::hash\'s measured table (spec 4.2).')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--write', action='store_true', help='measure and write every file')
    modes.add_argument('--check', action='store_true', help='the measure lane\'s check')
    modes.add_argument('--capabilities', action='store_true',
                       help='write doc/backends.adoc from doc/capabilities.json')
    modes.add_argument('--overrides', action='store_true',
                       help='write detail/overrides.hpp from doc/capabilities.json')
    parser.add_argument('--library', default=str(ROOT / 'libs/hash'))
    parser.add_argument('--measured', help='the measurements, instead of measuring')
    parser.add_argument('--programs', nargs='+', default=[],
                        help='the lists of programs the measure lane wrote')
    parser.add_argument('--build-dir', default=str(ROOT / 'bin/measure'))
    parser.add_argument('--invocations', type=int, default=INVOCATIONS)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--strip', default='strip')
    args = parser.parse_args(argv)
    try:
        if not (args.write or args.check or args.capabilities or args.overrides):
            raise Usage('give one of --write, --check, --capabilities and --overrides')
        if args.measured and args.programs:
            raise Usage('--measured and --programs are two sources of measurements: give one')
        if args.check and not (args.measured or args.programs):
            raise Usage('--check compares --measured or the lists of --programs')
        library = Library(Path(args.library).resolve())
        if args.capabilities:
            write_text(library.outputs()['backends'], render_backends(library.table))
        elif args.overrides:
            write_text(library.outputs()['overrides'], render_overrides(library.table))
        elif args.write:
            mode_write(library, args)
        else:
            mode_check(library, args)
    except Usage as e:
        print(f'measure.py: {e}', file=sys.stderr)
        return 2
    except Failure as e:
        print(f'measure.py: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

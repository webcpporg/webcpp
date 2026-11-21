#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Configures Botan for one target with upstream's configure.py, and lists its sources.

    configure.py --source CHECKOUT --modules MODULES --output DIRECTORY --os OS --cc CC --cpu CPU

runs CHECKOUT's own configure.py (CODING-GUIDELINES.md chapter 5, rule 13) with
--minimized-build and the modules MODULES lists (tools/botan/modules.txt), for OS, CC and CPU,
into DIRECTORY, unless DIRECTORY already holds a complete configuration, its
webcpp-configure.json. Upstream writes build/build.h, build/target_info.h, the public and internal
headers under build/include and build/build_config.json; nothing is written into CHECKOUT. The
configuration is written into a sibling, DIRECTORY.partial, first, and renamed into place once
complete, so that an interrupted run leaves no half configuration: the next run starts again.

It then prints one line per source, `lib <path>` for the library's and `test <path>` for its test
program's, each path relative to CHECKOUT with forward slashes, sorted. b2 compiles each as an
object of its own (tools/webcpp-botan.jam).

Upstream's configure.py is run with python3 -I, its working directory DIRECTORY's parent, and
without the environment variables it reads compiler settings from (CXX, CXXFLAGS, AR, AR_OPTIONS
and LDFLAGS), so that a configuration is a function of the arguments alone: --disable-cc-tests
keeps it from running a compiler. It refuses a configuration that loads a module seeding a
generator from the system (system_rng, auto_rng and the entropy sources): webcpp's libraries take
their randomness elsewhere.

Exit 0 on success; 1, with the reason on standard output, for a module upstream does not know, a
failed configure.py (its last lines printed), a source outside CHECKOUT, or a refused module.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

# The modules that seed a generator from the system, which no configuration may load.
REFUSED = ('system_rng', 'auto_rng', 'entropy', 'jitter_rng', 'processor_rng', 'esdm_rng')

# The environment variables upstream's configure.py takes compiler settings from.
COMPILER_VARIABLES = ('CXX', 'CXXFLAGS', 'AR', 'AR_OPTIONS', 'LDFLAGS')

# The file that makes a configuration directory complete, written last.
RECORD = 'webcpp-configure.json'

# The lines of upstream's output printed when it fails.
FAILURE_LINES = 20


class ConfigureError(Exception):
    """A configuration that cannot be made, with the reason to print."""


def read_modules(path: Path) -> list[str]:
    """The modules path lists, in the file's order: words, a # starting a comment."""
    modules: list[str] = []
    for line in path.read_text().splitlines():
        modules += line.split('#', 1)[0].split()
    return modules


def upstream_command(checkout: Path, modules: list[str], build: Path, output: Path,
                     target: tuple[str, str, str]) -> list[str]:
    """The command line of upstream's configure.py writing into build, for output's prefix."""
    system, compiler, cpu = target
    return [sys.executable, '-I', str(checkout / 'configure.py'), '--minimized-build',
            f'--enable-modules={",".join(modules)}', f'--os={system}', f'--cc={compiler}',
            f'--cpu={cpu}', '--cc-min-version=0.0', '--disable-cc-tests',
            '--disable-shared-library', '--without-documentation', '--link-method=copy',
            '--build-tool=ninja', f'--prefix={output / "prefix"}', f'--with-build-dir={build}']


def relative_sources(checkout: Path, sources: list[str]) -> list[str]:
    """sources, absolute paths, relative to checkout with forward slashes, sorted."""
    relative: list[str] = []
    for source in sources:
        path = Path(source).resolve()
        try:
            relative.append(path.relative_to(checkout).as_posix())
        except ValueError:
            raise ConfigureError(f'Botan source {source} is outside the checkout {checkout}') \
                from None
    return sorted(relative)


def run_upstream(checkout: Path, modules: list[str], output: Path,
                 target: tuple[str, str, str]) -> dict:
    """Configures into output.partial, checks it and renames it to output; returns its record."""
    partial = output.with_name(output.name + '.partial')
    if partial.exists():
        shutil.rmtree(partial)
    partial.parent.mkdir(parents=True, exist_ok=True)
    environment = {name: value for name, value in os.environ.items()
                   if name not in COMPILER_VARIABLES}
    result = subprocess.run(upstream_command(checkout, modules, partial, output, target),
                            cwd=partial.parent, env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        last = '\n'.join(result.stdout.rstrip().splitlines()[-FAILURE_LINES:])
        raise ConfigureError(f"Botan's configure.py failed ({result.returncode}):\n{last}")
    configuration = json.loads((partial / 'build' / 'build_config.json').read_text())
    loaded = set(configuration['mod_list'])
    refused = sorted(loaded.intersection(REFUSED))
    if refused:
        raise ConfigureError('Botan modules that seed a generator from the system are loaded: '
                             f'{" ".join(refused)}; remove what pulls them in from '
                             'tools/botan/modules.txt')
    missing = [module for module in modules if module not in loaded]
    if missing:
        raise ConfigureError(f'Botan did not load the modules {" ".join(missing)}')
    record = {'target': list(target), 'modules': modules,
              'lib': relative_sources(checkout, configuration['lib_srcs']),
              'test': relative_sources(checkout, configuration['test_srcs'])}
    (partial / RECORD).write_text(json.dumps(record, indent=1) + '\n')
    if output.exists():
        shutil.rmtree(output)
    partial.rename(output)
    return record


def configure(checkout: Path, modules: list[str], output: Path,
              target: tuple[str, str, str]) -> dict:
    """The record of output's configuration, made first unless output is complete."""
    record = output / RECORD
    if record.is_file():
        return json.loads(record.read_text())
    return run_upstream(checkout, modules, output, target)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Configures Botan for one target with upstream's configure.py, and lists "
                    'its sources.')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--modules', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--os', required=True)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--cpu', required=True)
    options = parser.parse_args(arguments)
    try:
        record = configure(options.source.resolve(), read_modules(options.modules),
                           options.output.resolve(), (options.os, options.cc, options.cpu))
    except ConfigureError as error:
        print(error)
        return 1
    lines = [f'lib {path}' for path in record['lib']] + \
        [f'test {path}' for path in record['test']]
    # Bytes, so that a Windows console adds no carriage return b2 would read into a path.
    sys.stdout.flush()
    sys.stdout.buffer.write(''.join(f'{line}\n' for line in lines).encode())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

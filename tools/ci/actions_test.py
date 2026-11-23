#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks the shell steps of tools/ci/actions: download.sh keeps a file only when its SHA-256 is
the pinned one, tries again a connection the server drops, exits 1 and leaves no file when the
digest differs or the download fails; and the
Boost action's install.sh refuses an empty or relative prefix before it downloads anything, since
b2 given an empty --prefix installs into /usr/local, installs b2 in <prefix>/bin and the headers
in <prefix>/include/boost on every runner, Windows's included, where the default layouts would put
b2 in <prefix> itself and the headers in <prefix>/include/boost-1_92, keeps in <prefix>/source the
archive's boost/version.hpp and every libs/<library>/src, which configure names in
user-config.jam, and fails, before the prefix is cached, when the prefix holds no headers, no b2 or
no sources after the install; it installs the headers with every patch of its patches/ applied,
also in a tree inside a git repository, keys its cache on them, fails, naming the patch, on one
that the archive holds already, one that does not apply and one outside the headers, and configure
refuses a prefix whose headers lack one; each patch names its upstream fix; its source step fills
a directory with the same tree alone, and
the marker it writes last, in place of a tree whose marker says the action wrote it, refuses any
other directory before it downloads anything, and leaves the tree as it was and nothing behind
when it fails. The wit-bindgen action
installs the build of the runner's system and processor, the program alone, in .local/wit-bindgen,
where the build looks for it, in place of what was there, and refuses a runner it pins no build
for before it downloads anything; the wasi-sdk action installs the runner's build of wasi-sdk 34.0
in .local/wasi-sdk, in place of what was there, with the release's platform-independent sysroot and
compiler-rt builtins in place of the build's own, the same archives on every runner (outside a
runner, this machine's build), fails, naming the target, when the build has builtins for a target
the platform-independent archive has none for, and refuses a runner it pins no build for before it
downloads anything; the wasmtime action installs the pinned build for each runner
in RUNNER_TEMP/wasmtime, replaces an earlier install, exports its directory through GITHUB_PATH,
and refuses an unsupported runner before downloading; the wasi-wit action installs the wit/deps
directory of each crate, wasip2's and wasip3's, in .local/wasi-wit/p2 and .local/wasi-wit/p3,
in place of what was
there, and fails, naming the crate, on one that holds no WIT. The emsdk action installs the emsdk
repository at its pinned commit, fetched with git, in .local/emsdk, in place of what was there,
and fails when another commit is checked out; every archive emsdk installs is downloaded and
checked first, a release without Emscripten's node_modules fails before emsdk runs, and so does
one emsdk would download unpinned, before emsdk activate; it refuses a runner other than Linux and
macOS on x86-64 and arm64 before it downloads anything; its configure step fails, naming both
versions, on an emcc that is not Emscripten 6.0.11, installs the node wrapper, which refuses b2's
probe of --experimental-wasm-threads without a word, gives the jobs EM_CACHE by its resolved path,
outside the emsdk, and warms that cache, so that no b2 meets Emscripten's sanity check; and its
libraries step builds the system libraries the lanes link into that cache, or, for a job that
only parses (the input libraries: 'false', under the same key), the sysroot alone, a cache the
action never saves. The node action keys npm's
cache on the lock file of every directory a job runs npm ci in: tools/doc, tools/lint, every
library's oracle and the site. The third-party action's key.sh keys a job's cache of the
OpenSSL and libdatachannel configurations by the job, its runner image and the builds' inputs,
and the configurations under bin/third_party, which a fresh checkout, or either library alone,
lacks, under the Bash on PATH and /bin/bash, macOS's 3.2. Nothing is fetched
from the network: the downloads are file:// URLs or a server of the test's own on the loopback, git
is a stand-in, and install.sh runs against
a download.sh that only says it was called, or that hands it a stand-in archive. Run with the
names of some cases to run only those."""

from __future__ import annotations

import hashlib
import io
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path

CI = Path(__file__).resolve().parent
DOWNLOAD = CI / 'download.sh'
BOOST = CI / 'actions/boost/install.sh'
WIT_BINDGEN = CI / 'actions/wit-bindgen/install.sh'
WASMTIME = CI / 'actions/wasmtime/install.sh'
WASI_WIT = CI / 'actions/wasi-wit/install.sh'
WASI_SDK = CI / 'actions/wasi-sdk/install.sh'
EMSDK = CI / 'actions/emsdk/install.sh'
THIRD_PARTY = CI / 'actions/third-party/key.sh'
HELPERS = CI / 'helpers.sh'

# What the stand-in download.sh prints, and its exit status: install.sh got past its guards.
CALLED = 'download.sh was called'
CALLED_STATUS = 99


def run(*command: str | Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(['bash', *map(str, command)], capture_output=True, text=True,
                          check=False, env={**os.environ, **(env or {})})


def source(scratch: Path) -> tuple[Path, str]:
    """A file to download, and its SHA-256."""
    path = scratch / 'archive.tar.gz'
    path.write_bytes(b'the pinned bytes\n')
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_pinned_download_is_kept(scratch: Path) -> None:
    path, digest = source(scratch)
    file = scratch / 'downloaded'
    result = run(DOWNLOAD, path.as_uri(), digest, file)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert file.read_bytes() == path.read_bytes()
    assert f'SHA-256 {digest}' in result.stdout, result.stdout


def test_another_digest_leaves_no_file(scratch: Path) -> None:
    path, digest = source(scratch)
    file = scratch / 'downloaded'
    pinned = '0' * 64
    result = run(DOWNLOAD, path.as_uri(), pinned, file)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert f'has SHA-256 {digest}, and {pinned} is pinned' in result.stderr, result.stderr
    assert not file.exists()


def test_a_failed_download_exits_1_and_leaves_no_file(scratch: Path) -> None:
    file = scratch / 'downloaded'
    # A file left by an earlier attempt is not taken for this one's.
    file.write_bytes(b'partial')
    result = run(DOWNLOAD, (scratch / 'missing.tar.gz').as_uri(), '0' * 64, file)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert 'could not download' in result.stderr, result.stderr
    assert not file.exists()


class DroppingServer:
    """An HTTP server on the loopback whose first connection closes with no reply, as a server
    that drops a TLS handshake does, and which serves `body` on every later one."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.connections = 0
        self.listener = socket.create_server(('127.0.0.1', 0))
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self.listener.getsockname()[1]}/archive.tar.gz'

    def serve(self) -> None:
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            with connection:
                self.connections += 1
                if self.connections == 1:
                    continue
                connection.recv(65536)
                head = f'HTTP/1.1 200 OK\r\nContent-Length: {len(self.body)}\r\n'
                connection.sendall(f'{head}Connection: close\r\n\r\n'.encode() + self.body)

    def close(self) -> None:
        self.listener.close()
        self.thread.join(timeout=5)


def test_a_dropped_connection_is_tried_again(scratch: Path) -> None:
    path, digest = source(scratch)
    server = DroppingServer(path.read_bytes())
    file = scratch / 'downloaded'
    try:
        result = run(DOWNLOAD, server.url, digest, file,
                     env={'no_proxy': '127.0.0.1', 'NO_PROXY': '127.0.0.1'})
    finally:
        server.close()
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert server.connections == 2, server.connections
    assert file.read_bytes() == path.read_bytes()


def test_a_usage_error_exits_2(scratch: Path) -> None:
    result = run(DOWNLOAD, 'file:///nothing')
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert 'usage: tools/ci/download.sh <url> <sha256> <file>' in result.stderr, result.stderr


def boost_tree(scratch: Path) -> Path:
    """A copy of install.sh where it lives, beside a download.sh that only says it was called."""
    action = scratch / 'tools/ci/actions/boost'
    action.mkdir(parents=True)
    shutil.copy2(BOOST, action / 'install.sh')
    place_helpers(scratch)
    stand_in = scratch / 'tools/ci/download.sh'
    stand_in.write_text(f'#!/bin/sh\necho "{CALLED}" >&2\nexit {CALLED_STATUS}\n')
    stand_in.chmod(0o755)
    return action / 'install.sh'


def test_boost_refuses_an_empty_or_relative_prefix(scratch: Path) -> None:
    script = boost_tree(scratch)
    runner = {'RUNNER_OS': 'Linux', 'RUNNER_TEMP': str(scratch / 'temp'),
              'GITHUB_PATH': str(scratch / 'path')}
    for arguments in (['install'], ['install', ''], ['install', 'relative/prefix'],
                      ['configure'], ['configure', ''], ['configure', 'relative/prefix'],
                      ['source'], ['source', ''], [], ['other']):
        result = run(script, *arguments, env=runner)
        assert result.returncode == 2, (arguments, result.returncode, result.stderr)
        assert ('usage: install.sh key | install <prefix> | configure <prefix> | source '
                '<directory>') in result.stderr, (arguments, result.stderr)
        assert CALLED not in result.stderr, (arguments, result.stderr)
    assert not (scratch / '.local').exists()
    # An absolute prefix, a POSIX one or a Windows one with slashes, gets to the download.
    for prefix in (str(scratch / 'prefix'), 'D:/a/_temp/boost-1.92.0'):
        result = run(script, 'install', prefix, env=runner)
        assert result.returncode == CALLED_STATUS, (prefix, result.returncode, result.stderr)
        assert CALLED in result.stderr, (prefix, result.stderr)


# A stand-in for b2, as bootstrap.sh builds it: --version, the headers' install, and the install
# of b2 itself from tools/build, where the layout decides where b2 goes. On Windows, Boost's
# boostcpp.jam defaults to --layout=versioned, which installs the headers in
# <prefix>/include/boost-1_92/boost, and b2's Jamroot to the portable layout, which puts b2 in
# --prefix and ignores --bindir; the system and standard layouts, the defaults elsewhere, put them
# in <prefix>/include/boost and --bindir. The stand-in takes Windows's defaults, so that only an
# install that names both layouts finds the headers and b2 where configure looks for them. It
# installs the headers of the tree it runs in. With STAND_IN_INSTALLS_NOTHING set, it installs
# nothing and succeeds.
FAKE_B2 = r'''#!/usr/bin/env bash
set -euo pipefail
prefix='' bindir='' layout=portable headers=boost-1_92
for argument in "$@"; do
    case "$argument" in
        --version) echo 'B2 5.5.3 (stand-in)'; exit 0 ;;
        --prefix=*) prefix="${argument#--prefix=}" ;;
        --bindir=*) bindir="${argument#--bindir=}" ;;
        --layout=system) headers=. ;;
        b2-install-layout=*) layout="${argument#b2-install-layout=}" ;;
    esac
done
if [ -n "${STAND_IN_INSTALLS_NOTHING-}" ]; then
    exit 0
elif [ -z "$bindir" ]; then
    mkdir -p "$prefix/include/$headers"
    cp -R boost "$prefix/include/$headers/boost"
elif [ "$layout" = standard ]; then
    mkdir -p "$bindir" && cp "$0" "$bindir/b2"
else
    mkdir -p "$prefix" && cp "$0" "$prefix/b2"
fi
'''


# A header of the stand-in archive with a defect, its two lines repeated, and the patch that
# removes them, as tools/ci/actions/boost/patches holds one.
DEFECT = 'int f()\n{\nint f()\n{\n    return 0;\n}\n'
FIXED = 'int f()\n{\n    return 0;\n}\n'
DEFECT_PATCH = '''The stand-in defect, fixed upstream by https://github.com/boostorg/example/pull/1.

diff --git a/boost/defect.hpp b/boost/defect.hpp
--- a/boost/defect.hpp
+++ b/boost/defect.hpp
@@ -1,6 +1,4 @@
 int f()
 {
-int f()
-{
     return 0;
 }
'''


def boost_patches(scratch: Path, patch: str = DEFECT_PATCH) -> Path:
    """tools/ci/actions/boost/patches of the scratch superproject, with patch in it."""
    patches = scratch / 'tools/ci/actions/boost/patches'
    patches.mkdir()
    (patches / 'defect.patch').write_text(patch)
    return patches / 'defect.patch'


def boost_archive(scratch: Path) -> Path:
    """A boost_1_92_0.tar.gz whose bootstrap.sh writes the stand-in b2."""
    tree = scratch / 'archive/boost_1_92_0'
    (tree / 'tools/build').mkdir(parents=True)
    for path, text in (('boost/version.hpp', '#define BOOST_VERSION 109200\n'),
                       ('boost/defect.hpp', DEFECT),
                       ('libs/url/src/url.cpp', '// url\n'),
                       ('libs/url/src/detail/pattern.hpp', '// pattern\n'),
                       ('libs/json/src/src.cpp', '// json\n'),
                       ('libs/charconv/src/from_chars.cpp', '// charconv\n'),
                       ('libs/locale/src/message.cpp', '// locale\n'),
                       ('libs/cobalt/src/this_thread.cpp', '// cobalt\n'),
                       ('libs/cobalt/src/main.cpp', '// cobalt main\n'),
                       ('libs/cobalt/src/detail/util.cpp', '// cobalt detail\n'),
                       ('libs/cobalt/src/io/sleep.cpp', '// cobalt io\n'),
                       ('libs/cobalt/src/io/ssl.cpp', '// cobalt ssl\n'),
                       ('libs/context/src/asm/jump_arm64_aapcs_macho_gas.S', '// context asm\n'),
                       ('libs/context/src/posix/stack_traits.cpp', '// context stack\n'),
                       ('libs/url/doc/index.html', '<p>not kept</p>\n')):
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_text(text)
    (tree / 'b2.in').write_text(FAKE_B2)
    bootstrap = tree / 'bootstrap.sh'
    bootstrap.write_text('#!/bin/sh\ncp b2.in b2 && chmod +x b2\n')
    bootstrap.chmod(0o755)
    archive = scratch / 'boost_1_92_0.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(tree, arcname='boost_1_92_0')
    return archive


def boost_install_tree(scratch: Path) -> tuple[Path, dict[str, str]]:
    """install.sh beside a download.sh that serves the stand-in archive, and a runner's
    variables."""
    script = boost_tree(scratch)
    archive = boost_archive(scratch)
    # Boost's gzip archive, the one every runner's tar reads by itself: Windows Server 2022's
    # tar.exe has no bzip2, and hung on the bzip2 archive until the job timed out.
    (scratch / 'tools/ci/download.sh').write_text(
        '#!/bin/sh\n'
        'case "$1" in\n'
        '    https://archives.boost.io/release/1.92.0/source/boost_1_92_0.tar.gz) ;;\n'
        '    *) echo "download.sh: not the archive: $1" >&2; exit 1 ;;\n'
        'esac\n'
        f'cp "{archive}" "$3"\n')
    (scratch / 'temp').mkdir()
    return script, {'RUNNER_OS': 'Linux', 'RUNNER_TEMP': str(scratch / 'temp'),
                    'GITHUB_PATH': str(scratch / 'path')}


def test_boost_installs_b2_and_the_headers_where_configure_finds_them(scratch: Path) -> None:
    script, runner = boost_install_tree(scratch)
    prefix = scratch / 'prefix'
    result = run(script, 'install', prefix, env=runner)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    installed = sorted(str(p.relative_to(prefix)) for p in prefix.rglob('*'))
    assert (prefix / 'bin/b2').is_file(), installed
    assert (prefix / 'include/boost/version.hpp').is_file(), installed
    result = subprocess.run(['bash', str(script), 'configure', str(prefix)], capture_output=True,
                            text=True, check=False, cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert (scratch / 'path').read_text() == f'{prefix}/bin\n'


def test_boost_install_fails_when_the_prefix_is_incomplete(scratch: Path) -> None:
    script, runner = boost_install_tree(scratch)
    prefix = scratch / 'prefix'
    result = run(script, 'install', prefix, env={**runner, 'STAND_IN_INSTALLS_NOTHING': '1'})
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert f'install.sh: {prefix} holds no Boost headers, no b2 or no sources' in (
        result.stderr), result.stderr


# What install keeps in <prefix>/source, and source writes into a directory: the archive's
# boost/version.hpp and every libs/<library>/src, and the marker that says the action wrote the
# tree, nothing else.
MARKER = '.webcpp-boost-source'
KEPT_SOURCES = [MARKER, 'boost/version.hpp', 'libs/charconv/src/from_chars.cpp',
                'libs/cobalt/src/detail/util.cpp', 'libs/cobalt/src/io/sleep.cpp',
                'libs/cobalt/src/io/ssl.cpp', 'libs/cobalt/src/main.cpp',
                'libs/cobalt/src/this_thread.cpp',
                'libs/context/src/asm/jump_arm64_aapcs_macho_gas.S',
                'libs/context/src/posix/stack_traits.cpp', 'libs/json/src/src.cpp',
                'libs/locale/src/message.cpp', 'libs/url/src/detail/pattern.hpp',
                'libs/url/src/url.cpp']

# Where source runs: no runner around it.
NO_RUNNER = {'RUNNER_OS': '', 'RUNNER_TEMP': '', 'GITHUB_PATH': ''}


def files_under(directory: Path) -> list[str]:
    return sorted(str(path.relative_to(directory)) for path in directory.rglob('*')
                  if path.is_file())


def pinned_sha256() -> str:
    found = re.search(r'^sha256=([0-9a-f]{64})$', BOOST.read_text(), re.MULTILINE)
    assert found, BOOST
    return found.group(1)


def expect_marker(tree: Path) -> None:
    """Asserts that tree's marker names the version and the archive's SHA-256."""
    text = (tree / MARKER).read_text()
    assert 'version=1.92.0\n' in text and f'sha256={pinned_sha256()}\n' in text, text


def test_boost_keeps_the_sources_of_its_compiled_libraries(scratch: Path) -> None:
    script, runner = boost_install_tree(scratch)
    prefix = scratch / 'prefix'
    result = run(script, 'install', prefix, env=runner)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert files_under(prefix / 'source') == KEPT_SOURCES, files_under(prefix / 'source')
    expect_marker(prefix / 'source')
    result = subprocess.run(['bash', str(script), 'configure', str(prefix)], capture_output=True,
                            text=True, check=False, cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 0, (result.returncode, result.stderr)
    config = (scratch / '.local/user-config.jam').read_text()
    assert f'modules.poke : BOOST_SOURCE : "{prefix}/source" ;\n' in config, config


def test_boost_configure_refuses_a_cached_prefix_with_stale_sources(scratch: Path) -> None:
    # A prefix cached before install kept the sources of every compiled library, or before it
    # wrote its marker, passes the headers and b2 but must not reach a build that needs them.
    script, runner = boost_install_tree(scratch)
    prefix = scratch / 'prefix'
    result = run(script, 'install', prefix, env=runner)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    for stale in ((prefix / 'source' / MARKER), (prefix / 'source/libs/cobalt/src'),
                  (prefix / 'source/libs/context/src')):
        kept = scratch / 'kept'
        shutil.move(stale, kept)
        result = subprocess.run(['bash', str(script), 'configure', str(prefix)],
                                capture_output=True, text=True, check=False, cwd=scratch,
                                env={**os.environ, **runner})
        assert result.returncode == 1, (stale, result.returncode, result.stderr)
        assert 'holds no Boost headers, no b2 or no sources' in result.stderr, result.stderr
        shutil.move(kept, stale)


def test_boost_source_fills_a_directory_alone(scratch: Path) -> None:
    # A machine whose Boost comes from a package manager has no sources: source fills
    # .local/boost-source from the same archive, checked the same way, with no runner around it.
    script, _ = boost_install_tree(scratch)
    directory = scratch / 'local sources'
    temp = scratch / 'tmp'
    temp.mkdir()
    for _ in range(2):
        # The second run replaces the tree the first wrote, which its marker says.
        result = run(script, 'source', directory, env={**NO_RUNNER, 'TMPDIR': str(temp)})
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        assert files_under(directory) == KEPT_SOURCES, files_under(directory)
        expect_marker(directory)
        # Nothing is left beside it, nor in the temporary directory.
        assert sorted(path.name for path in scratch.glob('local sources*')) == [
            'local sources'], list(scratch.iterdir())
        assert list(temp.iterdir()) == [], list(temp.iterdir())
    assert not (scratch / '.local').exists()


def test_boost_source_refuses_a_directory_it_did_not_write(scratch: Path) -> None:
    # Only a tree that install.sh wrote, which its marker says, is replaced; anything else is left
    # as it is, before anything is downloaded (the stand-in download.sh only says it was called):
    # a directory of the user's, an installed Boost's include directory, a whole Boost tree, and a
    # tree of the same shape as the action's that holds no marker, as one written before the
    # marker existed.
    script = boost_tree(scratch)
    for name, files in (('mine', ['keep.txt']),
                        ('include', ['boost/version.hpp', 'boost/url.hpp', 'zlib.h']),
                        ('boost_1_92_0', ['boost/version.hpp', 'boost/url.hpp', 'b2',
                                          'libs/url/doc/index.html', 'libs/url/src/url.cpp']),
                        ('unmarked', ['boost/version.hpp', 'libs/url/src/url.cpp'])):
        directory = scratch / name
        for file in files:
            (directory / file).parent.mkdir(parents=True, exist_ok=True)
            (directory / file).write_text(f'{file}\n')
        result = run(script, 'source', directory, env=NO_RUNNER)
        assert result.returncode == 1, (name, result.returncode, result.stdout, result.stderr)
        assert (f'install.sh: {directory} exists and holds no {MARKER}, so install.sh did not '
                'write it, and it is left as it is') in result.stderr, (name, result.stderr)
        assert 'remove it yourself' in result.stderr, (name, result.stderr)
        assert CALLED not in result.stderr, (name, result.stderr)
        assert files_under(directory) == sorted(files), (name, files_under(directory))


def broken_archive(scratch: Path, how: str) -> None:
    """Replaces the stand-in archive with one that cannot be read, or one without
    boost/version.hpp, so that source fails after it made its temporary directories."""
    archive = scratch / 'boost_1_92_0.tar.gz'
    if how == 'unreadable':
        archive.write_bytes(b'not a gzip archive\n')
        return
    tree = scratch / 'broken/boost_1_92_0'
    (tree / 'libs/url/src').mkdir(parents=True)
    (tree / 'libs/url/src/url.cpp').write_text('// url\n')
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(tree, arcname='boost_1_92_0')


def test_boost_source_that_fails_leaves_the_tree_and_no_files(scratch: Path) -> None:
    # A source that fails, in the archive or while it copies, leaves the tree it wrote before as
    # it was, and removes what it made: the extracted archive, and the tree it was filling.
    script, _ = boost_install_tree(scratch)
    directory = scratch / 'local sources'
    temp = scratch / 'tmp'
    temp.mkdir()
    environment = {**NO_RUNNER, 'TMPDIR': str(temp)}
    result = run(script, 'source', directory, env=environment)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    for how in ('unreadable', 'without version.hpp'):
        broken_archive(scratch, how)
        result = run(script, 'source', directory, env=environment)
        assert result.returncode != 0, (how, result.returncode, result.stdout, result.stderr)
        assert files_under(directory) == KEPT_SOURCES, (how, files_under(directory))
        assert sorted(path.name for path in scratch.glob('local sources*')) == [
            'local sources'], (how, list(scratch.iterdir()))
        assert list(temp.iterdir()) == [], (how, list(temp.iterdir()))


def test_boost_installs_patched_headers(scratch: Path) -> None:
    # The tree is patched before its headers are installed, also where it lies inside a git
    # repository, whose root git apply would otherwise read the patch's paths from, skipping
    # them without a word; and configure accepts the prefix.
    script, runner = boost_install_tree(scratch)
    boost_patches(scratch)
    subprocess.run(['git', 'init', '-q', str(scratch)], check=True)
    prefix = scratch / 'prefix'
    result = run(script, 'install', prefix, env=runner)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert 'install.sh: applied tools/ci/actions/boost/patches/defect.patch' in result.stdout, (
        result.stdout)
    assert (prefix / 'include/boost/defect.hpp').read_text() == FIXED
    result = subprocess.run(['bash', str(script), 'configure', str(prefix)], capture_output=True,
                            text=True, check=False, cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 0, (result.returncode, result.stderr)
    # A prefix whose headers lack a patch, one cached before it was added, is refused.
    (prefix / 'include/boost/defect.hpp').write_text(DEFECT)
    result = subprocess.run(['bash', str(script), 'configure', str(prefix)], capture_output=True,
                            text=True, check=False, cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert (f'install.sh: the Boost headers of {prefix} lack '
            'tools/ci/actions/boost/patches/defect.patch') in result.stderr, result.stderr


def test_boost_key_changes_with_the_patches(scratch: Path) -> None:
    # A digest of the action's files, of the patches with them, keys the cached prefix: a patch
    # added or changed installs Boost again.
    script = boost_tree(scratch)
    shutil.copy2(BOOST.parent / 'action.yml', script.parent / 'action.yml')
    # A macOS runner, whose image a stand-in sw_vers names, on any machine.
    tools = scratch / 'stand-in bin'
    tools.mkdir()
    (tools / 'sw_vers').write_text('#!/bin/sh\necho 15.7\n')
    (tools / 'sw_vers').chmod(0o755)
    output = scratch / 'output'
    runner = {'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64', 'RUNNER_TEMP': str(scratch / 'temp'),
              'GITHUB_OUTPUT': str(output), 'PATH': f'{tools}{os.pathsep}{os.environ["PATH"]}'}
    keys = []
    for patch in (None, DEFECT_PATCH, DEFECT_PATCH + '\n'):
        if patch is not None:
            shutil.rmtree(scratch / 'tools/ci/actions/boost/patches', ignore_errors=True)
            boost_patches(scratch, patch)
        output.write_text('')
        result = run(script, 'key', env=runner)
        assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr)
        keys.append(re.search(r'^key=(.+)$', output.read_text(), re.MULTILINE))
    assert all(keys) and len({key.group(1) for key in keys if key}) == 3, keys


def test_boost_fails_on_a_patch_that_does_not_apply(scratch: Path) -> None:
    # A patch is removed, not skipped: one that the archive holds already (a Boost that has the
    # fix), one that no longer applies, and one outside the headers each fail the install, naming
    # the patch, and the prefix is not written.
    script, runner = boost_install_tree(scratch)
    name = 'tools/ci/actions/boost/patches/defect.patch'
    outside = DEFECT_PATCH.replace('boost/defect.hpp', 'libs/url/src/url.cpp')
    stale = DEFECT_PATCH.replace(' int f()\n {\n-int f()', ' int g()\n {\n-int g()')
    for patch, archive, expected in (
            (DEFECT_PATCH, FIXED, f'Boost 1.92.0 holds the change of {name} already: '
             'remove the patch'),
            (stale, DEFECT, f'{name} does not apply to Boost 1.92.0: update it, or remove it'),
            (outside, DEFECT, f'{name} patches a file outside boost/, the headers')):
        shutil.rmtree(scratch / 'tools/ci/actions/boost/patches', ignore_errors=True)
        boost_patches(scratch, patch)
        tree = scratch / 'archive/boost_1_92_0'
        (tree / 'boost/defect.hpp').write_text(archive)
        with tarfile.open(scratch / 'boost_1_92_0.tar.gz', 'w:gz') as tar:
            tar.add(tree, arcname='boost_1_92_0')
        prefix = scratch / 'prefix'
        result = run(script, 'install', prefix, env=runner)
        assert result.returncode == 1, (expected, result.returncode, result.stdout,
                                        result.stderr)
        assert f'install.sh: {expected}' in result.stderr, (expected, result.stderr)
        assert not prefix.exists(), expected


def test_the_boost_patches_name_their_upstream_fix(_: Path) -> None:
    # Each patch says, in its opening paragraph, which upstream change makes it unnecessary.
    for patch in sorted((CI / 'actions/boost/patches').glob('*.patch')):
        opening = patch.read_text().split('\ndiff --git ', 1)[0]
        assert re.search(r'https://github\.com/boostorg/[\w-]+/(pull|issues|commit)/\w+',
                         opening), patch


def place_helpers(scratch: Path) -> None:
    """tools/ci/helpers.sh in the scratch superproject, where every action sources it."""
    (scratch / 'tools/ci').mkdir(parents=True, exist_ok=True)
    shutil.copy2(HELPERS, scratch / 'tools/ci/helpers.sh')


def serving_tree(scratch: Path, action: str, script: Path, archives: dict[str, Path]) -> Path:
    """A copy of the action's install.sh where it lives, beside a download.sh that serves each
    archive by the URL it is downloaded from, and writes each URL and digest it is given to
    downloads.log; any other URL fails it."""
    directory = scratch / 'tools/ci/actions' / action
    directory.mkdir(parents=True)
    shutil.copy2(script, directory / 'install.sh')
    place_helpers(scratch)
    cases = ''.join(f'    {url}) cp "{archive}" "$3" ;;\n' for url, archive in archives.items())
    stand_in = scratch / 'tools/ci/download.sh'
    stand_in.write_text('#!/bin/sh\n'
                        f'printf \'%s %s\\n\' "$1" "$2" >> "{scratch}/downloads.log"\n'
                        'case "$1" in\n'
                        f'{cases}'
                        '    *) echo "download.sh: not served: $1" >&2; exit 1 ;;\n'
                        'esac\n')
    stand_in.chmod(0o755)
    (scratch / 'temp').mkdir()
    return directory / 'install.sh'


def downloads(scratch: Path) -> list[tuple[str, str]]:
    """The (URL, digest) of each download the stand-in was asked for, in order."""
    log = scratch / 'downloads.log'
    if not log.exists():
        return []
    return [(url, digest) for url, _, digest in
            (line.partition(' ') for line in log.read_text().splitlines())]


def tar_gz(archive: Path, root: Path, top: str) -> Path:
    """archive, a gzip tarball of root's tree under the top directory top."""
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(root, arcname=top)
    return archive


WIT_BINDGEN_RELEASE = 'https://github.com/bytecodealliance/wit-bindgen/releases/download/v0.62.0'

# The runners the action pins a build of wit-bindgen 0.62.0 for, and the build's name.
WIT_BINDGEN_BUILDS = {
    ('Linux', 'X64'): 'x86_64-linux',
    ('Linux', 'ARM64'): 'aarch64-linux',
    ('macOS', 'ARM64'): 'aarch64-macos',
    ('macOS', 'X64'): 'x86_64-macos',
}


def wit_bindgen_archive(scratch: Path, build: str) -> Path:
    """A stand-in of the release's archive of build: its top directory, the program, which says
    its version, and the files beside it, which the action leaves out."""
    top = f'wit-bindgen-0.62.0-{build}'
    tree = scratch / 'archive' / build
    tree.mkdir(parents=True)
    program = tree / 'wit-bindgen'
    program.write_text(f'#!/bin/sh\necho "wit-bindgen-cli 0.62.0 (stand-in {build})"\n')
    program.chmod(0o755)
    (tree / 'LICENSE-MIT').write_text('licence\n')
    (tree / 'README.md').write_text('readme\n')
    return tar_gz(scratch / f'{top}.tar.gz', tree, top)


def test_wit_bindgen_installs_the_runners_build_alone(scratch: Path) -> None:
    digests = set()
    for (system, processor), build in WIT_BINDGEN_BUILDS.items():
        root = scratch / build
        root.mkdir()
        url = f'{WIT_BINDGEN_RELEASE}/wit-bindgen-0.62.0-{build}.tar.gz'
        script = serving_tree(root, 'wit-bindgen', WIT_BINDGEN,
                              {url: wit_bindgen_archive(root, build)})
        # What an earlier install left is not kept beside the new one.
        stale = root / '.local/wit-bindgen/stale'
        stale.parent.mkdir(parents=True)
        stale.write_text('stale\n')
        runner = {'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                  'RUNNER_TEMP': str(root / 'temp')}
        result = subprocess.run(['bash', str(script)], capture_output=True, text=True,
                                check=False, cwd=root, env={**os.environ, **runner})
        assert result.returncode == 0, (build, result.returncode, result.stderr)
        installed = root / '.local/wit-bindgen'
        assert sorted(p.name for p in installed.iterdir()) == ['wit-bindgen'], (
            build, list(installed.iterdir()))
        assert os.access(installed / 'wit-bindgen', os.X_OK), build
        assert f'wit-bindgen-cli 0.62.0 (stand-in {build})' in result.stdout, (
            build, result.stdout)
        [(downloaded, digest)] = downloads(root)
        assert downloaded == url, (build, downloaded)
        assert len(digest) == 64 and set(digest) <= set('0123456789abcdef'), (build, digest)
        digests.add(digest)
        assert list((root / 'temp').iterdir()) == [], build
    assert len(digests) == len(WIT_BINDGEN_BUILDS), digests


def test_wit_bindgen_refuses_a_runner_it_pins_no_build_for(scratch: Path) -> None:
    script = serving_tree(scratch, 'wit-bindgen', WIT_BINDGEN, {})
    for system, processor in (('Windows', 'X64'), ('Linux', 'ARM'), ('', '')):
        runner = {'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                  'RUNNER_TEMP': str(scratch / 'temp')}
        result = subprocess.run(['bash', str(script)], capture_output=True, text=True,
                                check=False, cwd=scratch, env={**os.environ, **runner})
        assert result.returncode == 1, (system, processor, result.returncode, result.stderr)
        assert (f'install.sh: no wit-bindgen 0.62.0 is pinned for {system} on {processor}'
                in result.stderr), result.stderr
    assert downloads(scratch) == []
    assert not (scratch / '.local').exists()


WASI_SDK_RELEASE = 'https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34'

# The runners the action pins a build of wasi-sdk 34.0 for, the build's name and its digest.
WASI_SDK_BUILDS = {
    ('Linux', 'X64'): (
        'x86_64-linux', 'b761e3a0721dbae9c09a0059e5fdb2bf917d1b4a8a7b430fb3b5aafb0984b2c4'),
    ('Linux', 'ARM64'): (
        'arm64-linux', 'f7e243dff54d60bcc576e94d6166b69f410f2500ae4a9ceef34315be10e77971'),
    ('macOS', 'ARM64'): (
        'arm64-macos', '9c59398106b417f8f14913380fdf0097a8cc0ff4af9eb3ce0065a859e88d49e9'),
    ('macOS', 'X64'): (
        'x86_64-macos', '87d27fa8adc68dee59bfbf2e22a6d34ef717c34d6bf1d8af2a56fc929d9ce0eb'),
}
# The release's platform-independent archives, the same on every runner.
WASI_SYSROOT = (f'{WASI_SDK_RELEASE}/wasi-sysroot-34.0.tar.gz',
                '9d813544eeebe38b7b8f2244ed591de46b6db812c6dd1a257ff9f0d2a905a2be')
WASI_BUILTINS = (f'{WASI_SDK_RELEASE}/libclang_rt-34.0.tar.gz',
                 'eee3e634dcf71aa22b1333391623cf5c9965a637dc428a27b1a858c026c587f1')
WASI_TARGETS = ('wasm32-unknown-wasip2', 'wasm32-unknown-wasip3')


def wasi_sdk_archives(scratch: Path, build: str, sdk_targets: tuple[str, ...] = WASI_TARGETS,
                      shared_targets: tuple[str, ...] = WASI_TARGETS) -> dict[str, Path]:
    """Stand-ins of the three archives the action downloads, by URL: the build's wasi-sdk, whose
    sysroot and builtins (of sdk_targets) say they are the build's, and the release's
    platform-independent sysroot and builtins (of shared_targets)."""
    sdk = scratch / 'archive' / build
    (sdk / 'bin').mkdir(parents=True)
    clang = sdk / 'bin/clang++'
    clang.write_text(f'#!/bin/sh\necho "clang version 23.1.0-wasi-sdk (stand-in {build})"\n')
    clang.chmod(0o755)
    (sdk / 'share/wasi-sysroot/lib/wasm32-wasip2').mkdir(parents=True)
    (sdk / 'share/wasi-sysroot/lib/wasm32-wasip2/libc++abi.a').write_text(f'{build}\n')
    (sdk / 'lib/clang/23/include').mkdir(parents=True)
    (sdk / 'lib/clang/23/include/stdint.h').write_text('header\n')
    for target in sdk_targets:
        (sdk / 'lib/clang/23/lib' / target).mkdir(parents=True)
        (sdk / 'lib/clang/23/lib' / target / 'libclang_rt.builtins.a').write_text(f'{build}\n')
    sysroot = scratch / 'archive/sysroot'
    (sysroot / 'lib/wasm32-wasip2').mkdir(parents=True)
    (sysroot / 'VERSION').write_text('34.0\n')
    (sysroot / 'lib/wasm32-wasip2/libc++abi.a').write_text('platform-independent\n')
    builtins = scratch / 'archive/builtins'
    for target in shared_targets:
        (builtins / target).mkdir(parents=True)
        (builtins / target / 'libclang_rt.builtins.a').write_text('platform-independent\n')
    return {
        f'{WASI_SDK_RELEASE}/wasi-sdk-34.0-{build}.tar.gz':
            tar_gz(scratch / f'wasi-sdk-34.0-{build}.tar.gz', sdk, f'wasi-sdk-34.0-{build}'),
        WASI_SYSROOT[0]: tar_gz(scratch / 'wasi-sysroot-34.0.tar.gz', sysroot,
                                'wasi-sysroot-34.0'),
        WASI_BUILTINS[0]: tar_gz(scratch / 'libclang_rt-34.0.tar.gz', builtins,
                                 'libclang_rt-34.0'),
    }


def tree_of(directory: Path) -> dict[str, str]:
    """Every file under directory, by its path relative to it, and its text."""
    return {path.relative_to(directory).as_posix(): path.read_text()
            for path in sorted(directory.rglob('*')) if path.is_file()}


def test_wasi_sdk_installs_the_platform_independent_sysroot_and_builtins(scratch: Path) -> None:
    for (system, processor), (build, digest) in WASI_SDK_BUILDS.items():
        root = scratch / build
        root.mkdir()
        script = serving_tree(root, 'wasi-sdk', WASI_SDK, wasi_sdk_archives(root, build))
        stale = root / '.local/wasi-sdk/stale'
        stale.parent.mkdir(parents=True)
        stale.write_text('stale\n')
        runner = {'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                  'RUNNER_TEMP': str(root / 'temp')}
        result = subprocess.run(['bash', str(script)], capture_output=True, text=True,
                                check=False, cwd=root, env={**os.environ, **runner})
        assert result.returncode == 0, (build, result.returncode, result.stderr)
        installed = root / '.local/wasi-sdk'
        assert f'stand-in {build}' in result.stdout, (build, result.stdout)
        assert tree_of(installed) == {
            'bin/clang++': f'#!/bin/sh\necho "clang version 23.1.0-wasi-sdk (stand-in {build})"\n',
            'lib/clang/23/include/stdint.h': 'header\n',
            'lib/clang/23/lib/wasm32-unknown-wasip2/libclang_rt.builtins.a':
                'platform-independent\n',
            'lib/clang/23/lib/wasm32-unknown-wasip3/libclang_rt.builtins.a':
                'platform-independent\n',
            'share/wasi-sysroot/VERSION': '34.0\n',
            'share/wasi-sysroot/lib/wasm32-wasip2/libc++abi.a': 'platform-independent\n',
        }, (build, tree_of(installed))
        assert downloads(root) == [(f'{WASI_SDK_RELEASE}/wasi-sdk-34.0-{build}.tar.gz', digest),
                                   WASI_SYSROOT, WASI_BUILTINS], (build, downloads(root))
        assert list((root / 'temp').iterdir()) == [], (build, list((root / 'temp').iterdir()))


def test_wasi_sdk_outside_a_runner_installs_this_machine_s_build(scratch: Path) -> None:
    system = {'Darwin': 'macOS', 'Linux': 'Linux'}.get(platform.system(), '')
    processor = {'arm64': 'ARM64', 'aarch64': 'ARM64', 'x86_64': 'X64',
                 'AMD64': 'X64'}.get(platform.machine(), '')
    if (system, processor) not in WASI_SDK_BUILDS:
        print('test_wasi_sdk_outside_a_runner_installs_this_machine_s_build: no wasi-sdk is '
              f'pinned for {platform.system()} on {platform.machine()}; skipped')
        return
    build, digest = WASI_SDK_BUILDS[(system, processor)]
    script = serving_tree(scratch, 'wasi-sdk', WASI_SDK, wasi_sdk_archives(scratch, build))
    environ = {k: v for k, v in os.environ.items()
               if k not in ('RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_TEMP')}
    result = subprocess.run(['bash', str(script)], capture_output=True, text=True, check=False,
                            cwd=scratch, env=environ)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert f'stand-in {build}' in result.stdout, result.stdout
    assert downloads(scratch)[0] == (f'{WASI_SDK_RELEASE}/wasi-sdk-34.0-{build}.tar.gz', digest)
    assert (scratch / '.local/wasi-sdk/share/wasi-sysroot/VERSION').is_file()


def test_wasi_sdk_fails_on_a_target_without_platform_independent_builtins(
        scratch: Path) -> None:
    archives = wasi_sdk_archives(scratch, 'x86_64-linux',
                                 sdk_targets=WASI_TARGETS + ('wasm32-unknown-wasip1',))
    script = serving_tree(scratch, 'wasi-sdk', WASI_SDK, archives)
    runner = {'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64', 'RUNNER_TEMP': str(scratch / 'temp')}
    result = subprocess.run(['bash', str(script)], capture_output=True, text=True, check=False,
                            cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert ('install.sh: libclang_rt-34.0.tar.gz has no builtins for wasm32-unknown-wasip1'
            in result.stderr), result.stderr
    assert list((scratch / 'temp').iterdir()) == []


def test_wasi_sdk_refuses_a_runner_it_pins_no_build_for(scratch: Path) -> None:
    script = serving_tree(scratch, 'wasi-sdk', WASI_SDK, {})
    for system, processor in (('Windows', 'X64'), ('Linux', 'ARM')):
        runner = {'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                  'RUNNER_TEMP': str(scratch / 'temp')}
        result = subprocess.run(['bash', str(script)], capture_output=True, text=True,
                                check=False, cwd=scratch, env={**os.environ, **runner})
        assert result.returncode == 1, (system, processor, result.returncode, result.stderr)
        assert (f'install.sh: no wasi-sdk 34.0 is pinned for {system} on {processor}'
                in result.stderr), result.stderr
    assert downloads(scratch) == []
    assert not (scratch / '.local').exists()


WASMTIME_RELEASE = 'https://github.com/bytecodealliance/wasmtime/releases/download/v50.0.1'

# Official release asset digests, also verified against the four downloaded archives.
WASMTIME_BUILDS = {
    ('Linux', 'X64'): (
        'x86_64-linux', '685466455dd42a14774a86c36c8f2e45cbb9bd6d92a850139315df60a75498a5'),
    ('Linux', 'ARM64'): (
        'aarch64-linux', 'd737e077416d78fbfb0a008229ec27d6a0fd5a4924874b8c38b293c850cf4094'),
    ('macOS', 'ARM64'): (
        'aarch64-macos', '960e5216c7ebd7e9b45e6561d15821b8b801b7d54aee28c7b91921aeb30c65c8'),
    ('macOS', 'X64'): (
        'x86_64-macos', 'ea1818fa8cbb51524847ab2ad22197e0051594fdc96cbd0cc2afb65832e11925'),
}


def wasmtime_archive(scratch: Path, build: str) -> Path:
    """The release's layout, with an executable identifying the selected build."""
    top = f'wasmtime-v50.0.1-{build}'
    tree = scratch / 'archive'
    tree.mkdir()
    program = tree / 'wasmtime'
    program.write_text(f'#!/bin/sh\necho "wasmtime 50.0.1 (stand-in {build})"\n')
    program.chmod(0o755)
    (tree / 'LICENSE').write_text('licence\n')
    archive = scratch / f'{top}.tar.xz'
    with tarfile.open(archive, 'w:xz') as tar:
        tar.add(tree, arcname=top)
    return archive


def test_wasmtime_installs_the_pinned_runners_build(scratch: Path) -> None:
    for (system, processor), (build, digest) in WASMTIME_BUILDS.items():
        root = scratch / build
        root.mkdir()
        asset = f'wasmtime-v50.0.1-{build}.tar.xz'
        url = f'{WASMTIME_RELEASE}/{asset}'
        script = serving_tree(root, 'wasmtime', WASMTIME,
                              {url: wasmtime_archive(root, build)})
        installed = root / 'temp/wasmtime'
        installed.mkdir()
        (installed / 'stale').write_text('stale\n')
        unrelated = root / 'temp/keep'
        unrelated.write_text('keep\n')
        github_path = root / 'github-path'
        github_path.write_text('/earlier/path\n')
        result = run(script, env={'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                                 'RUNNER_TEMP': str(root / 'temp'),
                                 'GITHUB_PATH': str(github_path)})
        assert result.returncode == 0, (build, result.returncode, result.stderr)
        assert f'wasmtime 50.0.1 (stand-in {build})' in result.stdout, (build, result.stdout)
        assert sorted(path.name for path in installed.iterdir()) == ['LICENSE', 'wasmtime']
        assert os.access(installed / 'wasmtime', os.X_OK), build
        assert github_path.read_text() == f'/earlier/path\n{installed}\n', build
        assert downloads(root) == [(url, digest)], (build, downloads(root))
        assert unrelated.read_text() == 'keep\n', build
        assert not (root / 'temp' / asset).exists(), build


def test_wasmtime_refuses_a_runner_it_pins_no_build_for(scratch: Path) -> None:
    script = serving_tree(scratch, 'wasmtime', WASMTIME, {})
    github_path = scratch / 'github-path'
    for system, processor in (('Windows', 'X64'), ('Linux', 'ARM'), ('', '')):
        result = run(script, env={'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                                 'RUNNER_TEMP': str(scratch / 'temp'),
                                 'GITHUB_PATH': str(github_path)})
        assert result.returncode == 1, (system, processor, result.returncode, result.stderr)
        assert f'no wasmtime 50.0.1 is pinned for {system} on {processor}' in result.stderr
    assert downloads(scratch) == []
    assert not github_path.exists()
    assert not (scratch / 'temp/wasmtime').exists()


# Each version's crate, the URL it is downloaded from, and its top directory.
WASI_CRATES = {
    'p2': ('https://static.crates.io/crates/wasip2/wasip2-1.0.4+wasi-0.2.12.crate',
           'wasip2-1.0.4+wasi-0.2.12'),
    'p3': ('https://static.crates.io/crates/wasip3/wasip3-0.9.0+wasi-0.3.0.crate',
           'wasip3-0.9.0+wasi-0.3.0'),
}


def wasi_crate(scratch: Path, version: str, deps: dict[str, str] | None) -> Path:
    """A stand-in of version's crate: its manifest, the crate's own world, and wit/deps with
    deps, each file's name and text; none when deps is None."""
    top = WASI_CRATES[version][1]
    tree = scratch / 'crates' / version
    (tree / 'wit').mkdir(parents=True)
    (tree / 'Cargo.toml').write_text('[package]\n')
    (tree / 'wit/wasi-crate.wit').write_text('package wasi:crate;\n')
    if deps is not None:
        (tree / 'wit/deps').mkdir()
        for name, text in deps.items():
            (tree / 'wit/deps' / name).write_text(text)
    return tar_gz(scratch / f'{top}.crate', tree, top)


WASI_DEPS = {
    'p2': {'http.wit': 'package wasi:http@0.2.12;\n', 'io.wit': 'package wasi:io@0.2.12;\n'},
    'p3': {'http.wit': 'package wasi:http@0.3.0;\n', 'cli.wit': 'package wasi:cli@0.3.0;\n'},
}


def test_wasi_wit_installs_each_crates_wit_deps(scratch: Path) -> None:
    archives = {WASI_CRATES[version][0]: wasi_crate(scratch, version, WASI_DEPS[version])
                for version in WASI_CRATES}
    script = serving_tree(scratch, 'wasi-wit', WASI_WIT, archives)
    stale = scratch / '.local/wasi-wit/p2/stale.wit'
    stale.parent.mkdir(parents=True)
    stale.write_text('stale\n')
    runner = {'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64', 'RUNNER_TEMP': str(scratch / 'temp')}
    result = subprocess.run(['bash', str(script)], capture_output=True, text=True, check=False,
                            cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 0, (result.returncode, result.stderr)
    for version, deps in WASI_DEPS.items():
        installed = scratch / '.local/wasi-wit' / version
        found = {p.name: p.read_text() for p in installed.iterdir()}
        assert found == deps, (version, found)
    assert [url for url, _ in downloads(scratch)] == [url for url, _ in WASI_CRATES.values()]
    digests = [digest for _, digest in downloads(scratch)]
    assert all(len(d) == 64 and set(d) <= set('0123456789abcdef') for d in digests), digests
    assert len(set(digests)) == 2, digests
    assert list((scratch / 'temp').iterdir()) == []


def test_wasi_wit_fails_on_a_crate_without_its_wit(scratch: Path) -> None:
    archives = {WASI_CRATES['p2'][0]: wasi_crate(scratch, 'p2', WASI_DEPS['p2']),
                WASI_CRATES['p3'][0]: wasi_crate(scratch, 'p3', None)}
    script = serving_tree(scratch, 'wasi-wit', WASI_WIT, archives)
    runner = {'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64', 'RUNNER_TEMP': str(scratch / 'temp')}
    result = subprocess.run(['bash', str(script)], capture_output=True, text=True, check=False,
                            cwd=scratch, env={**os.environ, **runner})
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert (f'install.sh: {WASI_CRATES["p3"][0]} holds no wit/deps/http.wit' in result.stderr), (
        result.stderr)
    assert not (scratch / '.local/wasi-wit/p3').exists()


EMSDK_COMMIT = 'dd8e25632640cfc1fb570c7fa4cc374e8a5e5a72'
EMSDK_REPOSITORY = 'https://github.com/emscripten-core/emsdk'
RELEASE = 'f6264d4a4dd9ba24a9f0a5702835a44d1463de13'
BUILDS = 'https://storage.googleapis.com/webassembly/emscripten-releases-builds'

# What emsdk 6.0.11 downloads for each runner, by URL, each saved under the name emsdk gives it in
# its downloads directory: the release's binaries, Node, and on macOS Python.
EMSDK_DOWNLOADS = {
    ('Linux', 'X64'): {
        f'{BUILDS}/linux/{RELEASE}/wasm-binaries.tar.xz': f'{RELEASE}-wasm-binaries.tar.xz',
        f'{BUILDS}/deps/node-v24.19.0-linux-x64.tar.xz': 'node-v24.19.0-linux-x64.tar.xz',
    },
    ('Linux', 'ARM64'): {
        f'{BUILDS}/linux/{RELEASE}/wasm-binaries-arm64.tar.xz':
            f'{RELEASE}-wasm-binaries-arm64.tar.xz',
        f'{BUILDS}/deps/node-v24.19.0-linux-arm64.tar.xz': 'node-v24.19.0-linux-arm64.tar.xz',
    },
    ('macOS', 'X64'): {
        f'{BUILDS}/mac/{RELEASE}/wasm-binaries.tar.xz': f'{RELEASE}-wasm-binaries.tar.xz',
        f'{BUILDS}/deps/node-v24.19.0-darwin-x64.tar.gz': 'node-v24.19.0-darwin-x64.tar.gz',
        f'{BUILDS}/deps/python-3.13.3-0-macos-x86_64.tar.gz':
            'python-3.13.3-0-macos-x86_64.tar.gz',
    },
    ('macOS', 'ARM64'): {
        f'{BUILDS}/mac/{RELEASE}/wasm-binaries-arm64.tar.xz':
            f'{RELEASE}-wasm-binaries-arm64.tar.xz',
        f'{BUILDS}/deps/node-v24.19.0-darwin-arm64.tar.gz': 'node-v24.19.0-darwin-arm64.tar.gz',
        f'{BUILDS}/deps/python-3.13.3-0-macos-arm64.tar.gz': 'python-3.13.3-0-macos-arm64.tar.gz',
    },
}

EMSCRIPTEN_VERSION = '6.0.11 (a0014542110d6078c3a1a7941fa1ddb3a2281f16)'

# The system libraries the action builds into the cache it saves: those that em++ links a program
# with at -O2 and at -O0 -g, with and without -fwasm-exceptions.
SYSTEM_LIBRARIES = [
    'libGL-getprocaddr', 'libal', 'libc', 'libc-debug', 'libc++-debug-legacyexcept',
    'libc++-debug-noexcept', 'libc++-legacyexcept', 'libc++-noexcept',
    'libc++abi-debug-legacyexcept', 'libc++abi-debug-noexcept', 'libc++abi-legacyexcept',
    'libc++abi-noexcept', 'libclang_rt.builtins', 'libclang_rt.builtins-legacysjlj', 'libdlmalloc',
    'libdlmalloc-debug', 'libhtml5', 'libnoexit', 'libsockets', 'libstubs', 'libstubs-debug',
    'libunwind-legacyexcept',
]

# A stand-in of git, for the commands the action runs: `init -q <dir>`, `-C <dir> fetch --depth 1
# <repository> <commit>`, which logs its repository and commit to git.log and copies the stand-in
# emsdk, STAND_IN_EMSDK, into <dir>, `-C <dir> checkout -q FETCH_HEAD`, and `-C <dir> rev-parse
# HEAD`, which prints STAND_IN_HEAD, else the commit fetched.
FAKE_GIT = r'''#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = init ]; then
    mkdir -p "$3/.git"
    exit 0
fi
[ "$1" = -C ] || { echo "git: not a command of the stand-in: $*" >&2; exit 1; }
directory="$2"
shift 2
case "$*" in
    'fetch --depth 1 '*)
        printf '%s %s\n' "$4" "$5" >> "${STAND_IN_LOG}"
        cp -R "${STAND_IN_EMSDK}/." "${directory}/"
        echo "$5" > "${directory}/.git/FETCH_HEAD"
        ;;
    'checkout -q FETCH_HEAD') ;;
    'rev-parse HEAD') echo "${STAND_IN_HEAD:-$(cat "${directory}/.git/FETCH_HEAD")}" ;;
    *) echo "git: not a command of the stand-in: $*" >&2; exit 1 ;;
esac
'''

# A stand-in of emsdk's own script: `install 6.0.11` installs nothing it would have to download,
# so it needs each archive the action pins in downloads/ and EMSDK_KEEP_DOWNLOADS=1, under which
# emsdk takes a file there for the download; it writes STAND_IN_EXTRA there too when that names a
# file, as an emsdk that downloads more than the action pins would. It installs an emcc and an
# em++ that print STAND_IN_VERSION, else 6.0.11's, and check Emscripten's configuration the first
# time they meet a cache, as Emscripten does, saying so on standard error; and an embuilder that
# logs what it is asked to build, and with which cache, to embuilder.log. `activate 6.0.11` writes
# the configuration, and fails when an unpinned download is still there.
FAKE_EMSDK = r'''#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
case "$*" in
    'install 6.0.11')
        [ "${EMSDK_KEEP_DOWNLOADS-}" = 1 ] || { echo 'emsdk: would download' >&2; exit 1; }
        for name in $(cat "$here/expected-downloads"); do
            [ -f "$here/downloads/$name" ] || { echo "emsdk: would download $name" >&2; exit 1; }
        done
        if [ -n "${STAND_IN_EXTRA-}" ]; then
            echo extra > "$here/downloads/$STAND_IN_EXTRA"
        fi
        mkdir -p "$here/upstream/emscripten/node_modules"
        for tool in emcc em++; do
            cat > "$here/upstream/emscripten/$tool" <<'TOOL'
#!/usr/bin/env bash
if [ ! -f "$EM_CACHE/sanity.txt" ]; then
    echo 'shared:INFO: (Emscripten: Running sanity checks)' >&2
    mkdir -p "$EM_CACHE" && echo checked > "$EM_CACHE/sanity.txt"
fi
version="${STAND_IN_VERSION:-6.0.11 (a0014542110d6078c3a1a7941fa1ddb3a2281f16)}"
echo "emcc (Emscripten gcc/clang-like replacement + linker emulating GNU ld) ${version}"
TOOL
            chmod +x "$here/upstream/emscripten/$tool"
        done
        cat > "$here/upstream/emscripten/embuilder" <<'TOOL'
#!/usr/bin/env bash
printf '%s %s\n' "$EM_CACHE" "$*" >> "$(dirname "$0")/../../embuilder.log"
TOOL
        chmod +x "$here/upstream/emscripten/embuilder"
        ;;
    'activate 6.0.11')
        if [ -n "${STAND_IN_EXTRA-}" ] && [ -e "$here/downloads/$STAND_IN_EXTRA" ]; then
            echo 'emsdk: activated with an unpinned download' >&2
            exit 1
        fi
        echo "LLVM_ROOT = '$here/upstream/bin'" > "$here/.emscripten"
        ;;
    *) echo "emsdk: not a command of the stand-in: $*" >&2; exit 1 ;;
esac
'''


def release_archive(path: Path, node_modules: bool) -> Path:
    """A stand-in of the release's binaries, an xz tarball under install/, with Emscripten's
    node_modules unless node_modules is False."""
    with tarfile.open(path, 'w:xz') as tar:
        for name in ('install/emscripten/emcc.py',
                     *(['install/emscripten/node_modules/acorn/package.json']
                       if node_modules else [])):
            data = f'{name}\n'.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return path


def emsdk_tree(scratch: Path, system: str, processor: str,
               node_modules: bool = True) -> tuple[Path, dict[str, str]]:
    """The emsdk action's files where they live, beside a download.sh that serves a stand-in of
    each archive the action pins for the runner, a stand-in git that serves the stand-in emsdk,
    and the runner's variables, its workspace reached through a link."""
    tree = scratch / 'stand-in emsdk'
    tree.mkdir(parents=True)
    script = tree / 'emsdk'
    script.write_text(FAKE_EMSDK)
    script.chmod(0o755)
    downloads = EMSDK_DOWNLOADS.get((system, processor), {})
    (tree / 'expected-downloads').write_text(''.join(f'{name}\n' for name in downloads.values()))
    (scratch / 'archive').mkdir()
    archives = {}
    for url, name in downloads.items():
        stand_in = scratch / 'archive' / name
        if 'wasm-binaries' in name:
            release_archive(stand_in, node_modules)
        else:
            stand_in.write_text(f'{url}\n')
        archives[url] = stand_in
    install = serving_tree(scratch, 'emsdk', EMSDK, archives)
    for name in ('node.sh', 'action.yml'):
        shutil.copy2(EMSDK.parent / name, install.parent / name)
    tools = scratch / 'tools-on-path'
    tools.mkdir()
    (tools / 'git').write_text(FAKE_GIT)
    (tools / 'git').chmod(0o755)
    # The workspace, by a link to it: what is installed lands in scratch itself.
    workspace = scratch / 'workspace link'
    workspace.symlink_to(scratch)
    return install, {'RUNNER_OS': system, 'RUNNER_ARCH': processor,
                     'RUNNER_TEMP': str(scratch / 'temp'), 'GITHUB_WORKSPACE': str(workspace),
                     'GITHUB_ENV': str(scratch / 'github-env'),
                     'GITHUB_OUTPUT': str(scratch / 'github-output'),
                     'PATH': f'{tools}{os.pathsep}{os.environ["PATH"]}',
                     'STAND_IN_EMSDK': str(tree), 'STAND_IN_LOG': str(scratch / 'git.log')}


def emsdk_step(scratch: Path, script: Path, step: str, runner: dict[str, str],
               **extra: str) -> subprocess.CompletedProcess:
    """Runs the emsdk action's step from the workspace, as the action does."""
    environment = {**os.environ, **runner, **extra}
    environment.pop('EM_CACHE', None)
    return subprocess.run(['bash', str(script), step], capture_output=True, text=True,
                          check=False, cwd=runner['GITHUB_WORKSPACE'], env=environment)


def fetched(scratch: Path) -> list[str]:
    """The (repository, commit) of each fetch the stand-in git was asked for, one line each."""
    log = scratch / 'git.log'
    return log.read_text().splitlines() if log.exists() else []


def test_emsdk_installs_the_pinned_emsdk_into_local_emsdk(scratch: Path) -> None:
    for (system, processor), pinned in EMSDK_DOWNLOADS.items():
        root = scratch / f'{system}-{processor}'
        root.mkdir()
        script, runner = emsdk_tree(root, system, processor)
        # What an earlier install left is not kept beside the new one.
        stale = root / '.local/emsdk/stale'
        stale.parent.mkdir(parents=True)
        stale.write_text('stale\n')
        result = emsdk_step(root, script, 'install', runner)
        assert result.returncode == 0, (system, processor, result.returncode, result.stderr)
        emsdk = root / '.local/emsdk'
        assert (emsdk / 'emsdk').is_file() and not stale.exists(), sorted(emsdk.iterdir())
        assert (emsdk / 'upstream/emscripten/emcc').is_file(), sorted(emsdk.iterdir())
        assert (emsdk / '.emscripten').is_file(), sorted(emsdk.iterdir())
        # emsdk is the repository at the pinned commit, without its git directory.
        assert fetched(root) == [f'{EMSDK_REPOSITORY} {EMSDK_COMMIT}'], fetched(root)
        assert not (emsdk / '.git').exists(), sorted(emsdk.iterdir())
        # The archives emsdk installed from are checked, then left out of what is cached.
        assert not (emsdk / 'downloads').exists(), sorted((emsdk / 'downloads').iterdir())
        assert [url for url, _ in downloads(root)] == [*pinned], downloads(root)
        digests = [digest for _, digest in downloads(root)]
        assert all(len(d) == 64 and set(d) <= set('0123456789abcdef') for d in digests), digests
        assert len(set(digests)) == len(digests), digests
        assert list((root / 'temp').iterdir()) == [], (system, processor)
        # The cache key names the version and the runner.
        result = emsdk_step(root, script, 'key', runner)
        assert result.returncode == 0, (result.returncode, result.stderr)
        key = (root / 'github-output').read_text()
        assert key.startswith('key=emsdk-6.0.11-') and f'-{processor}-' in key, key


def test_emsdk_fails_on_another_commit(scratch: Path) -> None:
    # The commit is the pin: a fetch that checks out another fails the install, naming both.
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    other = '1' * 40
    result = emsdk_step(scratch, script, 'install', runner, STAND_IN_HEAD=other)
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert (f'install.sh: {EMSDK_REPOSITORY} at {EMSDK_COMMIT} checked out {other}') in (
        result.stderr), result.stderr
    assert not (scratch / '.local/emsdk').exists()
    assert downloads(scratch) == []


def test_emsdk_fails_on_a_release_without_its_node_modules(scratch: Path) -> None:
    # emsdk would run npm ci against the registry for a release without Emscripten's
    # node_modules: the install fails first, naming the archive, and emsdk installs nothing.
    script, runner = emsdk_tree(scratch, 'Linux', 'X64', node_modules=False)
    result = emsdk_step(scratch, script, 'install', runner)
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert (f'install.sh: {RELEASE}-wasm-binaries.tar.xz holds no install/emscripten/'
            'node_modules, which emsdk would install with npm from the registry') in (
                result.stderr), result.stderr
    assert not (scratch / '.local/emsdk').exists()


def test_emsdk_configure_installs_the_wrapper_and_warms_the_cache(scratch: Path) -> None:
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    result = emsdk_step(scratch, script, 'install', runner)
    assert result.returncode == 0, (result.returncode, result.stderr)
    result = emsdk_step(scratch, script, 'configure', runner)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    # EM_CACHE by its resolved path, though the workspace is reached through a link, and outside
    # the emsdk.
    cache = scratch.resolve() / '.local/emscripten-cache'
    assert (scratch / 'github-env').read_text() == f'EM_CACHE={cache}\n', (
        (scratch / 'github-env').read_text())
    # Warmed: Emscripten checked its configuration here, in the action's log, and the b2 of a job
    # meets a cache that is checked already.
    assert (cache / 'sanity.txt').is_file(), sorted(cache.iterdir())
    assert 'Running sanity checks' in result.stdout + result.stderr, (result.stdout, result.stderr)
    # The node wrapper, which refuses b2's probe without a word, and runs node otherwise.
    wrapper = scratch / '.local/emscripten/node'
    assert os.access(wrapper, os.X_OK), wrapper
    probe = subprocess.run([str(wrapper), '--version', '--experimental-wasm-threads'],
                           capture_output=True, text=True, check=False)
    assert probe.returncode != 0 and probe.stdout == probe.stderr == '', probe
    (scratch / 'bin').mkdir()
    stand_in = scratch / 'bin/node'
    stand_in.write_text('#!/bin/sh\necho "node $*"\n')
    stand_in.chmod(0o755)
    ran = subprocess.run([str(wrapper), 'x y.js', '--flag'], capture_output=True, text=True,
                         check=False,
                         env={**os.environ, 'PATH': f'{scratch / "bin"}:/usr/bin:/bin'})
    assert (ran.returncode, ran.stdout) == (0, 'node x y.js --flag\n'), ran
    # Configured again over a restored cache, it checks nothing more and says so on no line.
    result = emsdk_step(scratch, script, 'configure', runner)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert 'Running sanity checks' not in result.stdout + result.stderr, result.stderr


def test_emsdk_builds_the_system_libraries_into_the_cache(scratch: Path) -> None:
    # The cache the action saves holds the system libraries the lanes link, built with embuilder
    # in the cache configure gives the jobs, so that no lane builds them.
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    for step in ('install', 'configure', 'libraries'):
        result = emsdk_step(scratch, script, step, runner)
        assert result.returncode == 0, (step, result.returncode, result.stdout, result.stderr)
    cache = scratch.resolve() / '.local/emscripten-cache'
    built = (scratch / '.local/emsdk/embuilder.log').read_text().splitlines()
    assert built == [f'{cache} build {" ".join(SYSTEM_LIBRARIES)}'], built


def test_emsdk_for_a_job_that_only_parses(scratch: Path) -> None:
    # A job that parses Emscripten's headers and links nothing, the docs and the lint, gives the
    # input libraries: 'false': the key is the same, so it restores the cache the lanes save,
    # its system libraries built; on a miss it writes the headers and the sysroot alone, with
    # embuilder build sysroot, and never saves that cache, which the lanes would restore without
    # their libraries.
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    keys = []
    for libraries in ('true', 'false'):
        (scratch / 'github-output').unlink(missing_ok=True)
        result = emsdk_step(scratch, script, 'key', runner, LIBRARIES=libraries)
        assert result.returncode == 0, (result.returncode, result.stderr)
        written = dict(line.split('=', 1)
                       for line in (scratch / 'github-output').read_text().splitlines())
        assert written['libraries'] == libraries, written
        keys.append(written['key'])
    assert keys[0] == keys[1], keys
    result = emsdk_step(scratch, script, 'key', runner, LIBRARIES='some')
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "install.sh: the input libraries is 'true' or 'false', not 'some'" in result.stderr, (
        result.stderr)
    for step in ('install', 'configure'):
        result = emsdk_step(scratch, script, step, runner)
        assert result.returncode == 0, (step, result.returncode, result.stderr)
    result = emsdk_step(scratch, script, 'libraries', runner, LIBRARIES='false')
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    cache = scratch.resolve() / '.local/emscripten-cache'
    built = (scratch / '.local/emsdk/embuilder.log').read_text().splitlines()
    assert built == [f'{cache} build sysroot'], built
    # The action passes the input to both steps, and saves the cache only when the libraries
    # were built.
    action = (EMSDK.parent / 'action.yml').read_text()
    steps = {step.split('\n', 1)[0]: step for step in action.split('    - name: ')[1:]}
    assert "LIBRARIES: ${{ inputs.libraries }}" in steps['Cache key'], steps['Cache key']
    assert "steps.key.outputs.libraries == 'true'" in steps['Save emsdk'], steps['Save emsdk']
    assert "LIBRARIES: ${{ inputs.libraries }}" in steps["Build Emscripten's system libraries"]
    assert re.search(r"^  libraries:\n(    .*\n)*    default: 'true'$", action, re.MULTILINE), (
        action)


def test_the_jamroot_pins_the_action_s_version(_: Path) -> None:
    # The Jamroot refuses an emsdk of another version than the one the action installs, for a
    # reference's Emscripten headers: both name one version.
    pinned = re.search(r'^version=(\S+)$', EMSDK.read_text(), re.MULTILINE)
    jamroot = re.search(r'^\.emscripten-version = (\S+) ;$',
                        (CI.parents[1] / 'Jamroot').read_text(), re.MULTILINE)
    assert pinned and jamroot and pinned.group(1) == jamroot.group(1), (pinned, jamroot)


def test_node_caches_every_lock_file_npm_ci_reads(_: Path) -> None:
    # A lock file left out of the key is installed from the registry on every run: the site's is
    # read by b2 site's npm ci, in the site job and the site's own lane.
    action = (CI / 'actions/node/action.yml').read_text()
    paths = re.search(r'^        cache-dependency-path: \|\n((?:          .*\n)+)', action,
                      re.MULTILINE)
    assert paths, action
    listed = [line.strip() for line in paths.group(1).splitlines()]
    assert listed == ['tools/doc/package-lock.json', 'tools/lint/package-lock.json',
                      'libs/*/test/oracle/package-lock.json', 'libs/*/js/package-lock.json',
                      'site/package-lock.json'], listed


def test_emsdk_configure_fails_naming_both_versions(scratch: Path) -> None:
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    result = emsdk_step(scratch, script, 'install', runner)
    assert result.returncode == 0, (result.returncode, result.stderr)
    other = '6.0.10 (0000000000000000000000000000000000000000)'
    result = emsdk_step(scratch, script, 'configure', runner, STAND_IN_VERSION=other)
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert (f'install.sh: .local/emsdk/upstream/emscripten/emcc is not Emscripten '
            f'{EMSCRIPTEN_VERSION}: emcc --version printed') in result.stderr, result.stderr
    assert other in result.stderr, result.stderr
    assert not (scratch / 'github-env').exists()


def test_emsdk_fails_on_a_download_it_does_not_pin(scratch: Path) -> None:
    # Before emsdk activate, which runs on macOS with the Python the install just unpacked.
    script, runner = emsdk_tree(scratch, 'Linux', 'X64')
    result = emsdk_step(scratch, script, 'install', runner, STAND_IN_EXTRA='llvm.tar.xz')
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert ('install.sh: emsdk downloaded llvm.tar.xz, which this action does not pin') in (
        result.stderr), result.stderr
    assert 'activated with an unpinned download' not in result.stderr, result.stderr
    assert not (scratch / '.local/emsdk').exists()


def test_emsdk_refuses_a_runner_it_pins_nothing_for(scratch: Path) -> None:
    for system, processor in (('Windows', 'X64'), ('Linux', 'ARM'), ('', '')):
        root = scratch / f'runner {system or "none"}'
        root.mkdir()
        script, runner = emsdk_tree(root, system, processor)
        for step in ('install', 'configure', 'libraries'):
            result = emsdk_step(root, script, step, runner)
            assert result.returncode == 1, (system, processor, step, result.returncode)
            assert (f'install.sh: no emsdk 6.0.11 is pinned for {system} on {processor}: the '
                    'action runs on Linux and macOS, on X64 and ARM64') in result.stderr, (
                        result.stderr)
        assert downloads(root) == [] and fetched(root) == []
        assert not (root / '.local').exists()


# A stand-in of a compiler, which says what it is as gcc's --version's first line does.
FAKE_COMPILER = '#!/bin/sh\necho "$(basename "$0") (stand-in) ${STAND_IN_VERSION:-14.2.0}"\n'


def stand_ins(scratch: Path, tools: dict[str, str]) -> Path:
    """A directory of the stand-in programs tools names, each by its text."""
    directory = scratch / 'tools-on-path'
    directory.mkdir(exist_ok=True)
    for name, text in tools.items():
        (directory / name).write_text(text)
        (directory / name).chmod(0o755)
    return directory


def logged(scratch: Path) -> list[str]:
    """The lines the stand-ins wrote, in order."""
    log = scratch / 'stand-in.log'
    return log.read_text().splitlines() if log.exists() else []


def dependency_runner(scratch: Path, system: str, processor: str, tools: Path,
                      **extra: str) -> dict[str, str]:
    """A runner's variables, with the stand-ins first on PATH."""
    return {'RUNNER_OS': system, 'RUNNER_ARCH': processor, 'RUNNER_TEMP': str(scratch / 'temp'),
            'ImageOS': 'ubuntu24', 'ImageVersion': '20261004.327.1',
            'GITHUB_OUTPUT': str(scratch / 'github-output'),
            'GITHUB_ENV': str(scratch / 'github-env'), 'GITHUB_PATH': str(scratch / 'github-path'),
            'PATH': f'{tools}{os.pathsep}{os.environ["PATH"]}',
            'STAND_IN_LOG': str(scratch / 'stand-in.log'), **extra}


def dependency_step(scratch: Path, script: Path, runner: dict[str, str],
                    *arguments: str) -> subprocess.CompletedProcess:
    """Runs the action's script from the scratch superproject, as the action does."""
    environment = {**os.environ, **runner}
    for name in ('CC', 'CXX', 'EMSCRIPTEN', 'OPENSSL_ROOT'):
        if name not in runner:
            environment.pop(name, None)
    return subprocess.run(['bash', str(script), *arguments], capture_output=True, text=True,
                          check=False, cwd=scratch, env=environment)



CHROME = CI / 'actions/chrome/install.sh'
CHROME_VERSION = '155.0.8059.39'
CHROME_BUILDS = {
    'X64': ('linux64', '39dcb8c46550632a3d911850ab3b8af840b4e3f6d8622faa2018eb8756278786'),
    'ARM64': ('linux-arm64', '9fb86f7c0b2734c5febc0bbb4e85f37da43553f3f8a7970949828c5713e87e94'),
}


def chrome_archive(scratch: Path, build: str, product: str = 'chrome-headless-shell') -> Path:
    """A stand-in of the shell's zip: its top directory, a program that prints its arguments, and
    the files beside it."""
    archive = scratch / f'{product}-{build}.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        program = zipfile.ZipInfo(f'{product}-{build}/{product}')
        program.external_attr = 0o755 << 16
        zipped.writestr(program, '#!/bin/sh\necho "shell $*"\n')
        zipped.writestr(f'{product}-{build}/ABOUT', 'about\n')
    return archive


def test_chrome_installs_the_pinned_headless_shell(scratch: Path) -> None:
    # Chrome for Testing's chrome-headless-shell at its pinned version, checked against the
    # SHA-256 recorded for the runner's build, in .local/chrome-headless-shell, and CHROME its
    # wrapper, which runs it with --no-sandbox and the arguments it is given.
    for processor, (build, digest) in CHROME_BUILDS.items():
        root = scratch / processor
        root.mkdir()
        url = (f'https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}/{build}/'
               f'chrome-headless-shell-{build}.zip')
        script = serving_tree(root, 'chrome', CHROME, {url: chrome_archive(root, build)})
        stale = root / '.local/chrome-headless-shell/stale'
        stale.parent.mkdir(parents=True)
        stale.write_text('stale\n')
        runner = dependency_runner(root, 'Linux', processor, stand_ins(root, {}))
        result = dependency_step(root, script, runner)
        assert result.returncode == 0, (processor, result.returncode, result.stderr)
        assert downloads(root) == [(url, digest)], downloads(root)
        assert not stale.exists() and list((root / 'temp').iterdir()) == []
        wrapper = root.resolve() / '.local/chrome-headless-shell/chrome'
        assert (root / 'github-env').read_text() == f'CHROME={wrapper}\n'
        ran = subprocess.run([str(wrapper), '--headless=new', 'x y'], capture_output=True,
                             text=True, check=False)
        assert (ran.returncode, ran.stdout) == (0, 'shell --no-sandbox --headless=new x y\n'), ran
        assert f'chrome-headless-shell {CHROME_VERSION}' in result.stdout, result.stdout


def test_chrome_installs_full_chrome_for_isolated_certificate_trust(scratch: Path) -> None:
    builds = {
        'X64': ('linux64', '55672d1f392fd3e7b7a08621b6e804e6bcb39d40cf155504abb74b3a021ea8ea'),
        'ARM64': ('linux-arm64',
                  'b9d44e5d183260ca941a4c4d8d21c8a437d81ef778a489047ef98968b0475dc5'),
    }
    for processor, (build, digest) in builds.items():
        root = scratch / processor
        root.mkdir()
        url = (f'https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}/{build}/'
               f'chrome-{build}.zip')
        archive = chrome_archive(root, build, 'chrome')
        script = serving_tree(root, 'chrome', CHROME, {url: archive})
        runner = dependency_runner(root, 'Linux', processor, stand_ins(root, {}))
        runner['WEBCPP_CHROME_PRODUCT'] = 'chrome'
        result = dependency_step(root, script, runner)
        assert result.returncode == 0, (processor, result.stderr)
        assert downloads(root) == [(url, digest)], downloads(root)
        wrapper = root.resolve() / '.local/chrome/chrome'
        assert (root / 'github-env').read_text() == f'CHROME={wrapper}\n'
        ran = subprocess.run([str(wrapper), '--headless=new'], capture_output=True,
                             text=True, check=False)
        assert (ran.returncode, ran.stdout) == (0, 'shell --no-sandbox --headless=new\n'), ran
        (root / 'tools/ci/download.sh').write_text(
            f'#!/bin/sh\nexec bash "{DOWNLOAD}" "{archive.as_uri()}" "$2" "$3"\n')
        result = dependency_step(root, script, runner)
        assert result.returncode == 1 and f'and {digest} is pinned' in result.stderr, result
        runner['WEBCPP_CHROME_PRODUCT'] = '../invalid'
        result = dependency_step(root, script, runner)
        assert result.returncode == 1 and 'unsupported Chrome product' in result.stderr, result


def test_chrome_refuses_a_shell_it_does_not_pin_or_a_runner_it_has_none_for(scratch: Path) -> None:
    build, digest = CHROME_BUILDS['X64']
    url = (f'https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}/{build}/'
           f'chrome-headless-shell-{build}.zip')
    archive = chrome_archive(scratch, build)
    script = serving_tree(scratch, 'chrome', CHROME, {url: archive})
    # The real download.sh, given the stand-in: its SHA-256 is not the pinned one.
    (scratch / 'tools/ci/download.sh').write_text(
        f'#!/bin/sh\nexec bash "{DOWNLOAD}" "{archive.as_uri()}" "$2" "$3"\n')
    runner = dependency_runner(scratch, 'Linux', 'X64', stand_ins(scratch, {}))
    result = dependency_step(scratch, script, runner)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert f'and {digest} is pinned' in result.stderr, result.stderr
    assert not (scratch / '.local/chrome-headless-shell').exists()
    assert not (scratch / 'github-env').exists()
    for system, processor in (('macOS', 'ARM64'), ('Windows', 'X64'), ('Linux', 'ARM'), ('', '')):
        result = dependency_step(scratch, script, {**runner, 'RUNNER_OS': system,
                                                   'RUNNER_ARCH': processor})
        assert result.returncode == 1, (system, processor, result.returncode)
        assert (f'install.sh: no chrome-headless-shell {CHROME_VERSION} is pinned for {system} on '
                f'{processor}') in result.stderr, result.stderr


CONTAINER = CI / 'actions/container/install.sh'

# A controlled Docker boundary: ordinary actions may inspect and pull, never build.
FAKE_IMAGE_DOCKER = r"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "docker $*" >> "${STAND_IN_LOG}"
case "$1" in
    image) exit 1 ;;
    pull) exit "${STAND_IN_PULL_STATUS:-0}" ;;
    *) exit 2 ;;
esac
"""


def test_no_external_library_action_remains(scratch: Path) -> None:
    # libsecp256k1 is /third_party//secp256k1: no workflow step installs it, and its action,
    # which built the pinned archive with CMake into .local/, is gone.
    assert not (CI / 'actions/secp256k1').exists()
    root = CI.parents[1]
    for workflow in (root / '.github/workflows').glob('*.yml'):
        assert 'actions/secp256k1' not in workflow.read_text(), workflow


def test_container_pulls_the_pinned_image_without_building(scratch: Path) -> None:
    # The historical build/load path is replaced by consumption of the checked immutable pin.
    directory = scratch / 'tools/ci/actions/container'
    directory.mkdir(parents=True)
    for name in ('install.sh', 'action.yml'):
        shutil.copy2(CONTAINER.parent / name, directory / name)
    place_helpers(scratch)
    shutil.copy2(CI / 'environment.py', scratch / 'tools/ci/environment.py')
    (scratch / 'tools/ci/container').mkdir()
    shutil.copy2(CI / 'container/Dockerfile', scratch / 'tools/ci/container/Dockerfile')
    sys.path.insert(0, str(CI))
    import environment as prepared_environment
    image = 'ghcr.io/webcpporg/ci-environment@sha256:' + 'a' * 64
    prepared_environment.write_manifest(scratch / 'tools/ci/environments.json', {
        'native-linux-x64': {'image': image, 'recipe': prepared_environment.recipe(),
                            'source': 'b' * 40, 'archives': []}})
    tools = stand_ins(scratch, {'docker': FAKE_IMAGE_DOCKER})
    runner = dependency_runner(scratch, 'Linux', 'X64', tools)
    script = directory / 'install.sh'
    result = dependency_step(scratch, script, runner)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert logged(scratch) == [f'docker image inspect {image}', f'docker pull {image}']
    (scratch / 'stand-in.log').unlink()
    result = dependency_step(scratch, script, {**runner, 'STAND_IN_PULL_STATUS': '1'})
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert 'prepare-environments' in result.stderr, result.stderr
    assert logged(scratch) == [f'docker image inspect {image}', f'docker pull {image}']
    action = (directory / 'action.yml').read_text()
    assert 'actions/cache' not in action and 'install.sh build' not in action, action


def test_the_shared_helpers(scratch: Path) -> None:
    # tools/ci/helpers.sh, which every action's install.sh sources beside download.sh: digest,
    # the SHA-256 of its files one after the other; mixed, a path as Windows programs read it;
    # configuration, CMake's Debug on Windows, for b2's /MDd, else Release; and
    # compiler_identity, the first line of the --version of each of CC and CXX that is set, else
    # the image.
    one, two = scratch / 'one', scratch / 'two'
    one.write_text('one\n')
    two.write_text('two\n')
    tools = stand_ins(scratch, {'cygpath': '#!/bin/sh\nprintf \'cygpath %s %s\\n\' "$1" "$2"\n',
                                'gcc-14': FAKE_COMPILER, 'g++-14': FAKE_COMPILER})

    def helper(call: str, **variables: str) -> str:
        environment = {**os.environ, 'PATH': f'{tools}{os.pathsep}{os.environ["PATH"]}',
                       **variables}
        for name in ('CC', 'CXX'):
            if name not in variables:
                environment.pop(name, None)
        result = subprocess.run(['bash', '-c', f'set -euo pipefail; . "{HELPERS}"; {call}'],
                                capture_output=True, text=True, check=False, env=environment)
        assert result.returncode == 0, (call, result.returncode, result.stderr)
        return result.stdout

    expected = hashlib.sha256(b'one\ntwo\n').hexdigest()
    assert helper(f'digest "{one}" "{two}"') == f'{expected}\n'
    single = hashlib.sha256(b'one\n').hexdigest()
    assert helper(f'digest "{one}"') == f'{single}\n'
    assert helper('mixed /a/b', RUNNER_OS='Linux') == '/a/b\n'
    assert helper('mixed /a/b', RUNNER_OS='Windows') == 'cygpath -m /a/b\n'
    assert helper('configuration', RUNNER_OS='Windows') == 'Debug\n'
    assert helper('configuration', RUNNER_OS='macOS') == 'Release\n'
    assert helper('compiler_identity', CC='gcc-14', CXX='g++-14') == (
        'gcc-14 (stand-in) 14.2.0\ng++-14 (stand-in) 14.2.0\n')
    assert helper('compiler_identity', CC='gcc-14') == 'gcc-14 (stand-in) 14.2.0\n'
    assert helper('compiler_identity', ImageOS='win22', ImageVersion='1') == 'default win22 1\n'
    # Each action's script sources it, and defines none of the four itself.
    for script in sorted(CI.glob('actions/*/*.sh')):
        text = script.read_text()
        for name in ('digest', 'mixed', 'configuration', 'compiler_identity'):
            assert f'\n{name}() {{' not in text, (script, name)
        if re.search(r'\$\((digest|mixed|configuration|compiler_identity)\b', text):
            assert '. "${here}/../../helpers.sh"' in text, script


def bashes() -> list[str]:
    """Each bash an action's step may run in here: the one on PATH, and /bin/bash, which is Bash
    3.2 on macOS, the one the macOS runners run a step with."""
    found = {}
    for candidate in (shutil.which('bash'), '/bin/bash'):
        if candidate and os.access(candidate, os.X_OK):
            found.setdefault(os.path.realpath(candidate), candidate)
    return list(found.values())


def third_party_key(root: Path, bash: str, job: str = 'gcc-15',
                    **variables: str) -> tuple[subprocess.CompletedProcess, dict[str, str]]:
    """Runs the third-party action's key step in root, a checkout, as the action does, and
    returns what it wrote to GITHUB_OUTPUT."""
    output = root / 'github-output'
    output.unlink(missing_ok=True)
    environment = {**os.environ, 'JOB': job, 'INPUTS': 'fd7fb185cbfac59a' + '0' * 48,
                   'ImageOS': 'ubuntu26', 'ImageVersion': '20261111.196',
                   'GITHUB_OUTPUT': str(output), **variables}
    result = subprocess.run([bash, str(THIRD_PARTY)], capture_output=True, text=True,
                            check=False, cwd=root, env=environment)
    written = (dict(line.split('=', 1) for line in output.read_text().splitlines())
               if output.exists() else {})
    return result, written


def test_third_party_key_of_a_checkout_without_builds(scratch: Path) -> None:
    # A fresh checkout has no bin/third_party, nor has a job whose programs use neither library:
    # neither is an error, and neither has a configuration to save. A key holds no comma, which
    # a job's name may, nor a space.
    for bash in bashes():
        result, written = third_party_key(scratch, bash, 'own-Own lane (asio, tls)')
        assert result.returncode == 0, (bash, result.returncode, result.stderr)
        prefix = 'third-party-v1-own-Own-lane--asio--tls--ubuntu26-20261111.196-fd7fb185cbfac59a-'
        assert written['prefix'] == prefix, (bash, written)
        assert re.fullmatch(re.escape(prefix) + '[0-9a-f]{16}', written['key']), (bash, written)
        assert written['built'] == 'false', (bash, written)
    # Without the job or the inputs, the key would name no cache.
    for missing in ('JOB', 'INPUTS'):
        result, written = third_party_key(scratch, bashes()[0], **{missing: ''})
        assert result.returncode == 2, (missing, result.returncode, result.stderr)
        assert 'usage: key.sh' in result.stderr, (missing, result.stderr)
        assert written == {}, (missing, written)
    # The action keys both its steps with the script, which the tests run.
    action = (THIRD_PARTY.parent / 'action.yml').read_text()
    steps = {step.split('\n', 1)[0]: step for step in action.split('    - name: ')[1:]}
    assert 'run: bash tools/ci/actions/third-party/key.sh\n' in steps['Cache key'], (
        steps['Cache key'])


def test_third_party_key_names_the_configurations(scratch: Path) -> None:
    # The key is the prefix and a hash of the names of the configurations, which either
    # library's directory may hold alone: a job saves its cache under a new key when it built a
    # configuration its restored entry did not hold.
    openssl = scratch / 'bin/third_party/openssl'
    libdatachannel = scratch / 'bin/third_party/libdatachannel'
    for bash in bashes():
        keys = []
        shutil.rmtree(scratch / 'bin', ignore_errors=True)
        for made in (openssl / 'config-1', libdatachannel / 'config-2', openssl / 'config-1'):
            if made == libdatachannel / 'config-2':
                shutil.rmtree(openssl)
            made.mkdir(parents=True)
            result, written = third_party_key(scratch, bash)
            assert result.returncode == 0, (bash, made, result.returncode, result.stderr)
            assert written['built'] == 'true', (bash, made, written)
            assert written['key'].startswith(written['prefix']), (bash, written)
            # The same configurations give the same key, and a file there is no configuration.
            (made.parent / 'config-stray').write_text('stray\n')
            assert third_party_key(scratch, bash)[1] == written, (bash, made)
            keys.append(written['key'])
        assert len(set(keys)) == 3, (bash, keys)


CASES: list[Callable[[Path], None]] = [
    test_the_shared_helpers,
    test_third_party_key_of_a_checkout_without_builds,
    test_third_party_key_names_the_configurations,
    test_a_pinned_download_is_kept,
    test_another_digest_leaves_no_file,
    test_a_failed_download_exits_1_and_leaves_no_file,
    test_a_dropped_connection_is_tried_again,
    test_a_usage_error_exits_2,
    test_boost_refuses_an_empty_or_relative_prefix,
    test_boost_installs_b2_and_the_headers_where_configure_finds_them,
    test_boost_install_fails_when_the_prefix_is_incomplete,
    test_boost_keeps_the_sources_of_its_compiled_libraries,
    test_boost_configure_refuses_a_cached_prefix_with_stale_sources,
    test_boost_source_fills_a_directory_alone,
    test_boost_source_refuses_a_directory_it_did_not_write,
    test_boost_source_that_fails_leaves_the_tree_and_no_files,
    test_boost_installs_patched_headers,
    test_boost_key_changes_with_the_patches,
    test_boost_fails_on_a_patch_that_does_not_apply,
    test_the_boost_patches_name_their_upstream_fix,
    test_wit_bindgen_installs_the_runners_build_alone,
    test_wit_bindgen_refuses_a_runner_it_pins_no_build_for,
    test_wasi_sdk_installs_the_platform_independent_sysroot_and_builtins,
    test_wasi_sdk_outside_a_runner_installs_this_machine_s_build,
    test_wasi_sdk_fails_on_a_target_without_platform_independent_builtins,
    test_wasi_sdk_refuses_a_runner_it_pins_no_build_for,
    test_wasmtime_installs_the_pinned_runners_build,
    test_wasmtime_refuses_a_runner_it_pins_no_build_for,
    test_wasi_wit_installs_each_crates_wit_deps,
    test_wasi_wit_fails_on_a_crate_without_its_wit,
    test_emsdk_installs_the_pinned_emsdk_into_local_emsdk,
    test_emsdk_fails_on_another_commit,
    test_emsdk_fails_on_a_release_without_its_node_modules,
    test_emsdk_configure_installs_the_wrapper_and_warms_the_cache,
    test_emsdk_builds_the_system_libraries_into_the_cache,
    test_emsdk_for_a_job_that_only_parses,
    test_the_jamroot_pins_the_action_s_version,
    test_node_caches_every_lock_file_npm_ci_reads,
    test_emsdk_configure_fails_naming_both_versions,
    test_emsdk_fails_on_a_download_it_does_not_pin,
    test_emsdk_refuses_a_runner_it_pins_nothing_for,
    test_no_external_library_action_remains,
    test_container_pulls_the_pinned_image_without_building,
    test_chrome_installs_the_pinned_headless_shell,
    test_chrome_installs_full_chrome_for_isolated_certificate_trust,
    test_chrome_refuses_a_shell_it_does_not_pin_or_a_runner_it_has_none_for,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'actions_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp actions ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('actions_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

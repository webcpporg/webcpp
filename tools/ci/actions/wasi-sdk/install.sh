#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# The step of tools/ci/actions/wasi-sdk, and the install of wasi-sdk on a developer's machine:
# wasi-sdk 34.0 in .local/wasi-sdk, where the README installs it, its clang and tools those of the
# runner's system and processor (RUNNER_OS, RUNNER_ARCH), and its sysroot and its compiler-rt
# builtins the release's platform-independent ones, wasi-sysroot-34.0 and libclang_rt-34.0, on
# every host. Its clang++ builds the wasip2 and wasip3 lanes, which tools/ci/matrix.py registers,
# and its clang-format and clang-tidy are the lint's.
#
# Each per-host archive of wasi-sdk carries a sysroot and builtins of its own build, made on the
# machine that built that archive: wasi-sdk's libc++abi keeps __FILE__ strings with that
# machine's paths (/Users/runner/work/wasi-sdk/... in the macOS archive, /src/... in the Linux
# one), which become bytes of every program that links them. Replacing both with the release's
# platform-independent archives makes a WASI program the same bytes whichever host builds it,
# as webcpp::hash's measured table needs (libs/hash/test/measure).
#
# Usage, from the superproject's root: install.sh
# Outside a runner, RUNNER_OS and RUNNER_ARCH default to this machine's, and RUNNER_TEMP to a
# temporary directory of its own.
set -euo pipefail

if [ -z "${RUNNER_OS-}" ]; then
    case "$(uname -s)" in
        Darwin) RUNNER_OS=macOS ;;
        Linux) RUNNER_OS=Linux ;;
        *) RUNNER_OS="$(uname -s)" ;;
    esac
fi
if [ -z "${RUNNER_ARCH-}" ]; then
    case "$(uname -m)" in
        arm64|aarch64) RUNNER_ARCH=ARM64 ;;
        x86_64|amd64) RUNNER_ARCH=X64 ;;
        *) RUNNER_ARCH="$(uname -m)" ;;
    esac
fi

version=34.0
base=https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34
case "${RUNNER_OS}-${RUNNER_ARCH}" in
    Linux-X64)
        asset=wasi-sdk-${version}-x86_64-linux.tar.gz
        sha256=b761e3a0721dbae9c09a0059e5fdb2bf917d1b4a8a7b430fb3b5aafb0984b2c4
        ;;
    Linux-ARM64)
        asset=wasi-sdk-${version}-arm64-linux.tar.gz
        sha256=f7e243dff54d60bcc576e94d6166b69f410f2500ae4a9ceef34315be10e77971
        ;;
    macOS-ARM64)
        asset=wasi-sdk-${version}-arm64-macos.tar.gz
        sha256=9c59398106b417f8f14913380fdf0097a8cc0ff4af9eb3ce0065a859e88d49e9
        ;;
    macOS-X64)
        asset=wasi-sdk-${version}-x86_64-macos.tar.gz
        sha256=87d27fa8adc68dee59bfbf2e22a6d34ef717c34d6bf1d8af2a56fc929d9ce0eb
        ;;
    *)
        printf 'install.sh: no wasi-sdk %s is pinned for %s on %s\n' "${version}" \
            "${RUNNER_OS}" "${RUNNER_ARCH}" >&2
        exit 1
        ;;
esac
# The release's platform-independent sysroot and compiler-rt builtins, the same on every host.
sysroot=wasi-sysroot-${version}.tar.gz
sysroot_sha256=9d813544eeebe38b7b8f2244ed591de46b6db812c6dd1a257ff9f0d2a905a2be
builtins=libclang_rt-${version}.tar.gz
builtins_sha256=eee3e634dcf71aa22b1333391623cf5c9965a637dc428a27b1a858c026c587f1

temporary=
if [ -z "${RUNNER_TEMP-}" ]; then
    temporary="$(mktemp -d)"
    RUNNER_TEMP="${temporary}"
fi
staging=
cleanup() {
    rm -f -- "${RUNNER_TEMP}/${asset}" "${RUNNER_TEMP}/${sysroot}" "${RUNNER_TEMP}/${builtins}"
    [ -z "${staging}" ] || rm -rf -- "${staging}"
    [ -z "${temporary}" ] || rm -rf -- "${temporary}"
}
trap cleanup EXIT

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${here}/../../download.sh" "${base}/${asset}" "${sha256}" "${RUNNER_TEMP}/${asset}"
"${here}/../../download.sh" "${base}/${sysroot}" "${sysroot_sha256}" "${RUNNER_TEMP}/${sysroot}"
"${here}/../../download.sh" "${base}/${builtins}" "${builtins_sha256}" \
    "${RUNNER_TEMP}/${builtins}"

rm -rf .local/wasi-sdk
mkdir -p .local/wasi-sdk
tar -xzf "${RUNNER_TEMP}/${asset}" -C .local/wasi-sdk --strip-components=1
staging="$(mktemp -d "${RUNNER_TEMP}/wasi-sdk-shared.XXXXXX")"
mkdir "${staging}/sysroot" "${staging}/builtins"
tar -xzf "${RUNNER_TEMP}/${sysroot}" -C "${staging}/sysroot" --strip-components=1
tar -xzf "${RUNNER_TEMP}/${builtins}" -C "${staging}/builtins" --strip-components=1

# The sysroot where clang looks for it, <prefix>/share/wasi-sysroot, in place of the archive's.
rm -rf .local/wasi-sdk/share/wasi-sysroot
mv "${staging}/sysroot" .local/wasi-sdk/share/wasi-sysroot

# The builtins of each WebAssembly target, in clang's resource directory, in place of the
# archive's: every target the archive has must be one the platform-independent archive has, so
# that no program links a per-host build of them.
resources=(.local/wasi-sdk/lib/clang/*/lib)
if [ "${#resources[@]}" -ne 1 ] || [ ! -d "${resources[0]}" ]; then
    printf 'install.sh: wasi-sdk %s has not one lib/clang/<version>/lib\n' "${version}" >&2
    exit 1
fi
for target in "${resources[0]}"/wasm32-*; do
    name="$(basename "${target}")"
    if [ ! -f "${staging}/builtins/${name}/libclang_rt.builtins.a" ]; then
        printf 'install.sh: %s has no builtins for %s\n' "${builtins}" "${name}" >&2
        exit 1
    fi
done
for target in "${staging}/builtins"/wasm32-*; do
    name="$(basename "${target}")"
    rm -rf "${resources[0]:?}/${name}"
    mv "${target}" "${resources[0]}/${name}"
done

.local/wasi-sdk/bin/clang++ --version
printf 'install.sh: the sysroot and builtins of wasi-sdk %s are the platform-independent %s and %s\n' \
    "${version}" "${sysroot}" "${builtins}"

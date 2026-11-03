#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# The step of tools/ci/actions/wasmtime: wasmtime 50.0.1 in RUNNER_TEMP/wasmtime, put on PATH
# (GITHUB_PATH), for the runner's system and processor (RUNNER_OS, RUNNER_ARCH). It runs the
# programs of the wasip2 lane directly and wasip3 through its launcher with network access, and
# serves the HTTP components of the own lanes on those targets and of the tests of the tools, as
# tools/component/serve.py's `wasmtime serve`.
#
# Usage: install.sh
set -euo pipefail

base=https://github.com/bytecodealliance/wasmtime/releases/download/v50.0.1
case "${RUNNER_OS}-${RUNNER_ARCH}" in
    Linux-X64)
        asset=wasmtime-v50.0.1-x86_64-linux.tar.xz
        sha256=685466455dd42a14774a86c36c8f2e45cbb9bd6d92a850139315df60a75498a5
        ;;
    Linux-ARM64)
        asset=wasmtime-v50.0.1-aarch64-linux.tar.xz
        sha256=d737e077416d78fbfb0a008229ec27d6a0fd5a4924874b8c38b293c850cf4094
        ;;
    macOS-ARM64)
        asset=wasmtime-v50.0.1-aarch64-macos.tar.xz
        sha256=960e5216c7ebd7e9b45e6561d15821b8b801b7d54aee28c7b91921aeb30c65c8
        ;;
    macOS-X64)
        asset=wasmtime-v50.0.1-x86_64-macos.tar.xz
        sha256=ea1818fa8cbb51524847ab2ad22197e0051594fdc96cbd0cc2afb65832e11925
        ;;
    *)
        printf 'install.sh: no wasmtime 50.0.1 is pinned for %s on %s\n' "${RUNNER_OS}" \
            "${RUNNER_ARCH}" >&2
        exit 1
        ;;
esac

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${here}/../../download.sh" "${base}/${asset}" "${sha256}" "${RUNNER_TEMP}/${asset}"
directory="${RUNNER_TEMP}/wasmtime"
rm -rf "${directory}"
mkdir -p "${directory}"
tar -xJf "${RUNNER_TEMP}/${asset}" -C "${directory}" --strip-components=1
rm "${RUNNER_TEMP}/${asset}"
printf '%s\n' "${directory}" >> "${GITHUB_PATH}"
"${directory}/wasmtime" --version

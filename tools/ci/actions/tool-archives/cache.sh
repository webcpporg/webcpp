#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# Per-tool archive cache identity and installation, always from the superproject's root.
# Usage: cache.sh <key|install> <tool> <variant>
# key writes directory and key to GITHUB_OUTPUT. install always runs the original installer,
# even after a cache hit, so its version check and GITHUB_PATH/GITHUB_ENV exports still run.
set -euo pipefail

if [ "$#" -ne 3 ]; then
    printf 'usage: cache.sh <key|install> <tool> <variant>\n' >&2
    exit 2
fi
operation="$1"
tool="$2"
variant="$3"
case "${operation}" in
    key|install) ;;
    *) printf 'cache.sh: unknown operation: %s\n' "${operation}" >&2; exit 2 ;;
esac
case "${tool}:${variant}" in
    wasi-sdk:|wasmtime:|wit-bindgen:|wasi-wit:|mrdocs:|chrome:chrome|chrome:chrome-headless-shell) ;;
    *) printf 'cache.sh: unsupported tool or variant: %s %s\n' "${tool}" "${variant}" >&2; exit 2 ;;
esac

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=../../helpers.sh
. "${here}/../../helpers.sh"
name="${tool}${variant:+-${variant}}"
directory="$(pwd)/.local/download-cache/${name}"
installer="tools/ci/actions/${tool}/install.sh"
case "${operation}" in
    key)
        identity="$(digest "${installer}" "tools/ci/actions/${tool}/action.yml" \
            tools/ci/download.sh tools/ci/helpers.sh "${here}/action.yml" "${here}/cache.sh" \
            tools/ci/environments.json)"
        printf 'directory=%s\nkey=tool-archives-%s-%s-%s-%s\n' "${directory}" "${name}" \
            "${RUNNER_OS}" "${RUNNER_ARCH}" "${identity}" >> "${GITHUB_OUTPUT}"
        ;;
    install)
        export WEBCPP_DOWNLOAD_CACHE="${directory}"
        if [ "${tool}" != chrome ] && [ "${RUNNER_OS}-${RUNNER_ARCH}" = Linux-X64 ] && \
                [ "${WEBCPP_PREPARE_ENVIRONMENT-}" != 1 ]; then
            export WEBCPP_DOWNLOAD_OFFLINE=1
        fi
        if [ "${tool}" = chrome ]; then
            export WEBCPP_CHROME_PRODUCT="${variant}"
        fi
        bash "${installer}"
        ;;
esac

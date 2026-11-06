#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# Downloads a pinned file and checks its SHA-256, for the actions of tools/ci/actions.
#
# Usage: tools/ci/download.sh <url> <sha256> <file>
# WEBCPP_DOWNLOAD_CACHE optionally names a directory of archives, each named by its SHA-256.
# WEBCPP_DOWNLOAD_OFFLINE=1 requires a verified cache hit and never invokes curl.
# Exit 0 with <file> written and its SHA-256 the one given; 1 when the download fails or the
# digest differs, which removes <file>; 2 on a usage error.
set -euo pipefail

if [ "$#" -ne 3 ]; then
    printf 'usage: tools/ci/download.sh <url> <sha256> <file>\n' >&2
    exit 2
fi
url="$1"
expected="$2"
file="$3"

if [[ ! "${expected}" =~ ^[[:xdigit:]]{64}$ ]]; then
    printf 'download.sh: expected a SHA-256 digest of 64 hexadecimal digits\n' >&2
    exit 2
fi
expected="$(printf '%s' "${expected}" | tr '[:upper:]' '[:lower:]')"
# Prefix a filename starting with '-' so it cannot become an option; keep Windows paths intact.
case "${file}" in -*) file="./${file}" ;; esac
temporary=
cache_temporary=
complete=false
cleanup() {
    [ -z "${temporary}" ] || rm -f -- "${temporary}"
    [ -z "${cache_temporary}" ] || rm -f -- "${cache_temporary}"
    if [ "${complete}" != true ]; then
        rm -f -- "${file}"
    fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

# The staged copy is hashed, not the cache path: a concurrent writer can replace a cache
# entry, but cannot change which bytes this invocation validates and delivers.
temporary="$(mktemp "${file}.tmp.XXXXXX")"
cache="${WEBCPP_DOWNLOAD_CACHE-}"
case "${cache}" in -*) cache="./${cache}" ;; esac
entry=
if [ -n "${cache}" ]; then
    mkdir -p -- "${cache}"
    entry="${cache}/${expected}"
    if [ -f "${entry}" ]; then
        cp -- "${entry}" "${temporary}"
    elif [ -e "${entry}" ]; then
        printf 'download.sh: cache entry is not a file: %s\n' "${entry}" >&2
        exit 1
    fi
fi

# sha256sum is GNU's (Linux, Git for Windows); macOS has shasum. Read stdin so a filename
# containing spaces or backslashes never changes the digest's printed representation.
sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum < "$1" | cut -d ' ' -f 1
    else
        shasum -a 256 < "$1" | cut -d ' ' -f 1
    fi
}

hit=false
if [ -n "${entry}" ] && [ -f "${entry}" ]; then
    actual="$(sha256 "${temporary}")"
    if [ "${actual}" = "${expected}" ]; then
        hit=true
    else
        printf 'download.sh: discarding corrupt cache entry %s (SHA-256 %s)\n' \
            "${entry}" "${actual}" >&2
        rm -f -- "${entry}"
    fi
fi
if [ "${hit}" != true ]; then
    if [ "${WEBCPP_DOWNLOAD_OFFLINE-}" = 1 ]; then
        printf 'download.sh: offline cache has no verified archive with SHA-256 %s\n' \
            "${expected}" >&2
        exit 1
    fi
    # --retry-all-errors also retries dropped TLS connections. Both each transfer and the
    # retry window are bounded; curl can finish one final transfer after that window ends.
    curl -fsSL --connect-timeout 30 --max-time 600 --retry 3 --retry-max-time 1200 \
        --retry-all-errors -o "${temporary}" "${url}" || {
        status=$?
        printf 'download.sh: could not download %s (curl exit status %s)\n' \
            "${url}" "${status}" >&2
        exit 1
    }
    actual="$(sha256 "${temporary}")"
    if [ "${actual}" != "${expected}" ]; then
        printf 'download.sh: %s has SHA-256 %s, and %s is pinned\n' "${url}" "${actual}" \
            "${expected}" >&2
        exit 1
    fi
    if [ -n "${entry}" ]; then
        cache_temporary="$(mktemp "${cache}/.download.XXXXXX")"
        cp -- "${temporary}" "${cache_temporary}"
        mv -f -- "${cache_temporary}" "${entry}"
        cache_temporary=
    fi
fi
mv -f -- "${temporary}" "${file}"
temporary=
complete=true
printf 'download.sh: %s, SHA-256 %s\n' "${url}" "${actual}"

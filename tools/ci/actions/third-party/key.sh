#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# The cache key of tools/ci/actions/third-party, which it computes before the job's b2, to
# restore, and after it, to save.
#
# Usage, from the superproject's root, with JOB, what keys the cache (such as the lane's id),
# INPUTS, the hash of the files the builds read, and the variables a runner sets (ImageOS,
# ImageVersion, GITHUB_OUTPUT):
#
#   key.sh   writes to GITHUB_OUTPUT the prefix, the job's cache on its runner image for those
#            inputs, whose most recent entry a job restores; the key, the prefix and a hash of the
#            names of the configurations under bin/third_party, under which a job saves them; and
#            built, whether there is any.
#
# A checkout without bin/third_party, a fresh one or that of a job whose programs use neither
# library, has no configuration, and nothing to save. Bash 3.2, the macOS runners', runs it too.
set -euo pipefail

if [ -z "${JOB-}" ] || [ -z "${INPUTS-}" ]; then
    printf 'usage: key.sh, with JOB and INPUTS set\n' >&2
    exit 2
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The functions every action shares: digest.
# shellcheck source=SCRIPTDIR/../../helpers.sh
. "${here}/../../helpers.sh"

# The runner image's compilers, and the job's: a key holds no comma, which a job's name may.
prefix="third-party-v1-${JOB//[^A-Za-z0-9._-]/-}-${ImageOS:-image}-${ImageVersion:-0}-"
prefix="${prefix}${INPUTS:0:16}-"

# The configurations' directories, of either library, whose own directory may not exist.
shopt -s nullglob
configurations=(bin/third_party/openssl/config-*/ bin/third_party/libdatachannel/config-*/)
# Given no file, digest hashes its standard input, as cat reads it.
# shellcheck disable=SC2119
names="$(printf '%s\n' ${configurations[@]+"${configurations[@]}"} | digest)"
built=false
if [ "${#configurations[@]}" -gt 0 ]; then
    built=true
fi

printf 'prefix=%s\nkey=%s%s\nbuilt=%s\n' "${prefix}" "${prefix}" "${names:0:16}" "${built}" \
    >> "${GITHUB_OUTPUT}"

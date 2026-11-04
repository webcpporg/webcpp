#!/usr/bin/env sh
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# The global P2 lane includes finite parsing workloads as well as loopback peers
# and host name lookup. Keep its process bound aligned with the P3 lane; focused
# networking tests can request a shorter bound without restricting the suite.
# Application deployments should grant only the capabilities they need.
webcpp_wasip2_timeout=${WEBCPP_WASIP2_TEST_TIMEOUT-600}
case "$webcpp_wasip2_timeout" in
    ''|*[!0-9]*) webcpp_wasip2_timeout= ;;
esac
case "$webcpp_wasip2_timeout" in
    *[1-9]*) ;;
    *)
        echo 'WEBCPP_WASIP2_TEST_TIMEOUT must be a positive integer number of seconds' >&2
        exit 2
        ;;
esac

exec wasmtime run -S inherit-network=y -S allow-ip-name-lookup=y \
    -W "timeout=${webcpp_wasip2_timeout}s" "$@"

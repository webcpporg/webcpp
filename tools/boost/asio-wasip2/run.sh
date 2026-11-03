#!/usr/bin/env sh
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# P2 regression programs use loopback peers and host name lookup.
# Application deployments should grant only the capabilities they need.
exec wasmtime run -S inherit-network=y -S allow-ip-name-lookup=y \
    -W timeout=60s "$@"

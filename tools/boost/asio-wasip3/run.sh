#!/usr/bin/env sh
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# Test launcher for local builds and CI using the project-pinned Wasmtime 50.0.1.
# Both single and cooperative thread profiles use the same runtime.
# Enabling the runtime's threading feature does not create application threads.
# Tests use loopback sockets and localhost resolution. Production applications
# should grant only the network capabilities they need.
exec wasmtime run -S p3 -S inherit-network=y -S allow-ip-name-lookup=y \
    -W component-model-async=y -W component-model-threading=y -W timeout=15s "$@"

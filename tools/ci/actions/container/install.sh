#!/usr/bin/env bash
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# Consume the reviewed digest. A missing registry image never starts an apt/image build.
# Usage, from the superproject's root: install.sh
set -euo pipefail
exec python3 tools/ci/environment.py native

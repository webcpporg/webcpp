# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)


"""Run the shared TLS peer with B2's executable argument placed last."""
from pathlib import Path
import subprocess
import sys

script = Path(__file__).with_name('tls.py')
subprocess.run([sys.executable, str(script), sys.argv[-1], *sys.argv[1:-1]],
               check=True, timeout=170)

# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Verify the ABI declarations shipped with Asio, without any former build overlay."""
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ABI(unittest.TestCase):
    def test_pinned_declarations_and_sdk(self):
        for profile in ('wasip2', 'wasip3'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                original = ROOT / 'libs/asio/src' / profile
                api = runpy.run_path(str(original / 'verify.py'))
                root = Path(temporary)
                bundle, sdk = root / 'bundle', root / 'sdk'
                shutil.copytree(original / 'wasi-libc', bundle / 'wasi-libc')
                sdk.mkdir()
                (sdk / 'VERSION').write_text('34.0\nwasi-libc: 2e6fb9d8ee0c\n')
                api['verify'](sdk, bundle)
                extra = bundle / 'wasi-libc/extra.h'
                extra.write_text('// Unlisted ABI declaration.\n')
                with self.assertRaisesRegex(ValueError, 'unlisted'):
                    api['verify_bundle'](bundle)
                extra.unlink()
                extra.symlink_to('wasi/poll.h')
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    api['verify_bundle'](bundle)
                extra.unlink()
                (sdk / 'VERSION').write_text('34.0\nwasi-libc: different\n')
                with self.assertRaisesRegex(ValueError, 'revalidate'):
                    api['verify'](sdk, bundle)
                header = bundle / 'wasi-libc/wasi/descriptor_table.h'
                header.write_text(header.read_text() + '\n/* changed ABI */\n')
                with self.assertRaisesRegex(ValueError, 'header changed'):
                    api['verify_bundle'](bundle)


if __name__ == '__main__':
    unittest.main()

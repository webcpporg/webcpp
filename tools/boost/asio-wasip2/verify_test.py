# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
import shutil
import tempfile
import unittest
from pathlib import Path
from verify import verify, verify_bundle

HERE = Path(__file__).resolve().parent


class ABI(unittest.TestCase):
    def test_unlisted_and_symlinked_files_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            shutil.copytree(HERE / 'wasi-libc', bundle / 'wasi-libc')
            extra = bundle / 'wasi-libc/unlisted.h'
            extra.write_text('// Not part of the pinned ABI.\n')
            with self.assertRaisesRegex(ValueError, 'unlisted'):
                verify_bundle(bundle)
            extra.unlink()
            extra.symlink_to('wasi/poll.h')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                verify_bundle(bundle)

    def test_sdk_revision_and_header_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sdk, bundle = root / 'sdk', root / 'bundle'
            sdk.mkdir()
            shutil.copytree(HERE / 'wasi-libc', bundle / 'wasi-libc')
            (sdk / 'VERSION').write_text('34.0\nwasi-libc: 2e6fb9d8ee0c\n')
            verify(sdk, bundle)
            (sdk / 'VERSION').write_text('34.0\nwasi-libc: different\n')
            with self.assertRaisesRegex(ValueError, 'revalidate'):
                verify(sdk, bundle)
            (sdk / 'VERSION').write_text('34.0\nwasi-libc: 2e6fb9d8ee0c\n')
            with (bundle / 'wasi-libc/wasi/descriptor_table.h').open('a') as header:
                header.write('\n/* incompatible edit */\n')
            with self.assertRaisesRegex(ValueError, 'header changed'):
                verify(sdk, bundle)


if __name__ == '__main__':
    unittest.main()

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import mdfiles
import os
import tempfile
import unittest


FILE_CONTENT = "test is a test"


class MdFilesTest(unittest.TestCase):

    def test_is_library_package(self):
        root_path = tempfile.mkdtemp("repo")
        package_path = "projects/libs/pastry/abstractions"
        md_dir_name = "MVN-INF"
        abs_package_path = os.path.join(root_path, package_path, md_dir_name)
        self._write_file(root_path, package_path, md_dir_name, "FOO", content="")
        self.assertFalse(mdfiles.is_library_package(abs_package_path))

        self._write_file(root_path, package_path, md_dir_name, "LIBRARY.root", content="")
        if not mdfiles.is_library_package(abs_package_path):
            package_content = str(os.listdir(abs_package_path))
            md_dir_content = str(os.listdir(os.path.join(abs_package_path, md_dir_name)))
            self.fail("Library marker file not found at path %s. Package has files: %s  md dir has files %s" % (abs_package_path, package_content, md_dir_content))

    def _write_file(self, root_path, package_path, md_path, file_name, content):
        path = os.path.join(root_path, package_path, md_path)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, file_name), "w") as f:
            f.write(content)


if __name__ == '__main__':
    unittest.main()

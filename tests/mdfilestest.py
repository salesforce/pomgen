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

    def setUp(self):
        self.org_md_dir_name = mdfiles.MD_DIR_NAME

    def tearDown(self):
        mdfiles.MD_DIR_NAME = self.org_md_dir_name

    def test_is_library_package(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        md_dir_name = "MVN-INF"
        mdfiles.MD_DIR_NAME = md_dir_name
        abs_package_path = os.path.join(root_path, package_path)

        self._write_file(root_path, package_path, md_dir_name, "FOO", content="")
        self.assertFalse(mdfiles.is_library_package(abs_package_path))
        self._write_file(root_path, package_path, md_dir_name, "LIBRARY.root", content="")
        if not mdfiles.is_library_package(abs_package_path):
            package_content = str(os.listdir(abs_package_path))
            md_dir_content = str(os.listdir(os.path.join(abs_package_path, md_dir_name)))
            self.fail("Library marker file not found at path %s. Package has files: %s  md dir has files %s" % (abs_package_path, package_content, md_dir_content))
    def test_is_artifact_package(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        md_dir_name = "MVN-INF"
        mdfiles.MD_DIR_NAME = md_dir_name
        abs_package_path = os.path.join(root_path, package_path)

        self._write_file(root_path, package_path, md_dir_name, "FOO", content="")
        self.assertFalse(mdfiles.is_artifact_package(abs_package_path))
        self._write_file(root_path, package_path, md_dir_name, "BUILD.pom", content="")
        self.assertTrue(mdfiles.is_artifact_package(abs_package_path))

    def test_read_file(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        self._write_file(root_path, package_path, "MVN-INF", "MYFILE", content=FILE_CONTENT)

        content, _ = mdfiles.read_file(root_path, package_path, "MYFILE")

        self.assertEqual(FILE_CONTENT, content)

    def test_read_file__md_dir_name(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        md_dir_name = "MVN-INF"
        self._write_file(root_path, package_path, md_dir_name, "MYFILE", content=FILE_CONTENT)
        mdfiles.MD_DIR_NAME = md_dir_name

        content, _ = mdfiles.read_file(root_path, package_path, "MYFILE")

        self.assertEqual(FILE_CONTENT, content)

    def test_write_file(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        os.makedirs(os.path.join(root_path, package_path))

        mdfiles.write_file(FILE_CONTENT, root_path, package_path, "MYFILE")

        content = self._read_file(root_path, package_path, "MVN-INF", "MYFILE")
        self.assertEqual(FILE_CONTENT, content)

    def test_write_file__md_dir_name(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        os.makedirs(os.path.join(root_path, package_path))
        md_dir_name = "MVN-INF"
        mdfiles.MD_DIR_NAME = md_dir_name

        mdfiles.write_file(FILE_CONTENT, root_path, package_path, "MYFILE")

        content = self._read_file(root_path, package_path, md_dir_name, "MYFILE")
        self.assertEqual(FILE_CONTENT, content)

    def test_write_file__package_must_exist(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"

        with self.assertRaises(Exception) as ex:
            mdfiles.write_file(FILE_CONTENT, root_path, package_path, "MYFILE")

        self.assertTrue("expected bazel package path to exist" in str(ex.exception))

    def test_move_files__root_dir_to_new_dir(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        self._write_file(root_path, package_path, "", "BUILD.pom", content=FILE_CONTENT)
        old_path = os.path.join(root_path, package_path, "BUILD.pom")
        self.assertTrue(os.path.exists(old_path))

        mdfiles.move_files(root_path, [package_path], "", "MVN-INF")

        self.assertFalse(os.path.exists(old_path))
        new_path = os.path.join(root_path, package_path, "MVN-INF", "BUILD.pom")
        self.assertTrue(os.path.exists(new_path))

    def test_move_files__old_dir_to_new_dir(self):
        root_path = tempfile.mkdtemp("monorepo")
        package_path = "projects/libs/pastry/abstractions"
        self._write_file(root_path, package_path, "OLD", "BUILD.pom", content=FILE_CONTENT)
        old_path = os.path.join(root_path, package_path, "OLD", "BUILD.pom")
        self.assertTrue(os.path.exists(old_path))

        mdfiles.move_files(root_path, [package_path], "OLD", "MVN")

        self.assertFalse(os.path.exists(old_path))
        new_path = os.path.join(root_path, package_path, "MVN", "BUILD.pom")
        self.assertTrue(os.path.exists(new_path))

    def _write_file(self, root_path, package_path, md_path, file_name, content):
        path = os.path.join(root_path, package_path, md_path)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, file_name), "w") as f:
            f.write(content)

    def _read_file(self, root_path, package_path, md_path, file_name):
        path = os.path.join(root_path, package_path, md_path, file_name)
        with open(path, "r") as f:
            return f.read()

if __name__ == '__main__':
    unittest.main()

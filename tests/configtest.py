"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from config import config
import unittest

class ConfigTest(unittest.TestCase):

    def test_pathsep__excluded_dependency_paths(self):
        cfg = config.Config(excluded_dependency_paths="abc")
        self.assertEqual("abc/", cfg.excluded_dependency_paths[0])

    def test_pathsep__excluded_src_relpaths(self):
        cfg = config.Config(excluded_src_relpaths="abc,  d/e/f")
        self.assertEqual("abc/", cfg.excluded_src_relpaths[0])
        self.assertEqual("d/e/f/", cfg.excluded_src_relpaths[1])

    def test_tuple__excluded_dependency_paths(self):
        cfg = config.Config(excluded_dependency_paths="abc/")
        self.assertTrue(isinstance(cfg.excluded_dependency_paths, tuple))
        self.assertEqual(1, len(cfg.excluded_dependency_paths))
        self.assertEqual("abc/", cfg.excluded_dependency_paths[0])

    def test_tuple__excluded_src_relpaths(self):
        cfg = config.Config(excluded_src_relpaths="abc/,  d/e/f/")
        self.assertTrue(isinstance(cfg.excluded_src_relpaths, tuple))
        self.assertEqual(2, len(cfg.excluded_src_relpaths))
        self.assertEqual("abc/", cfg.excluded_src_relpaths[0])
        self.assertEqual("d/e/f/", cfg.excluded_src_relpaths[1])

    def test_tuple__excluded_src_file_names(self):
        cfg = config.Config(excluded_src_file_names="name1, name2,  name3 ")
        self.assertTrue(isinstance(cfg.excluded_src_file_names, tuple))
        self.assertEqual(3, len(cfg.excluded_src_file_names))
        self.assertEqual("name1", cfg.excluded_src_file_names[0])
        self.assertEqual("name2", cfg.excluded_src_file_names[1])
        self.assertEqual("name3", cfg.excluded_src_file_names[2])

    def test_tuple__excluded_src_file_extensions(self):
        cfg = config.Config(excluded_src_file_extensions="")
        self.assertTrue(isinstance(cfg.excluded_src_file_extensions, tuple))
        self.assertEqual(0, len(cfg.excluded_src_file_extensions))

if __name__ == '__main__':
    unittest.main()
        

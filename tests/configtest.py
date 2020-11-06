"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from config import config
import os
import tempfile
import unittest

class ConfigTest(unittest.TestCase):

    def test_pom_template(self):
        repo_root = tempfile.mkdtemp("root")
        pom_template_path = self._write_file(repo_root, "pom_template", "pom")
        self._write_pomgenrc(repo_root, pom_template_path, ext_deps_path="")

        cfg = config.load(repo_root)

        self.assertEqual("pom", cfg.pom_template)

    def test_external_dependencies__single_file(self):
        repo_root = tempfile.mkdtemp("root")
        pom_template_path = self._write_file(repo_root, "pom_template", "foo")
        ext_deps_path = self._write_file(repo_root, "ext_deps", "abc")
        self._write_pomgenrc(repo_root, pom_template_path, ext_deps_path)

        cfg = config.load(repo_root)

        self.assertEqual("abc\n", cfg.external_dependencies)

    def test_external_dependencies__multiple_files(self):
        repo_root = tempfile.mkdtemp("root")
        pom_template_path = self._write_file(repo_root, "pom_template", "foo")
        ext_deps_p1 = self._write_file(repo_root, "ext_deps1", "abc")
        ext_deps_p2 = self._write_file(repo_root, "ext_deps2", "def")
        ext_deps_p3 = self._write_file(repo_root, "ext_deps3", "ghi")
        self._write_pomgenrc(repo_root, pom_template_path, 
                             "%s,%s,%s"%(ext_deps_p1, ext_deps_p2, ext_deps_p3))

        cfg = config.load(repo_root)

        self.assertEqual("abc\ndef\nghi\n", cfg.external_dependencies)

    def test_transitives_versioning_mode__semver(self):
        repo_root = tempfile.mkdtemp("root")
        os.mkdir(os.path.join(repo_root, "config"))
        pom_template_path = self._write_file(repo_root, "WORKSPACE", "foo")
        pom_template_path = self._write_file(repo_root, "config/pom_template.xml", "foo")
        self._write_file(repo_root, ".pomgenrc", """
[artifact]
transitives_versioning_mode=semver
""")

        cfg = config.load(repo_root)

        self.assertEqual("semver", cfg.transitives_versioning_mode)

    def test_transitives_versioning_mode__counter(self):
        repo_root = tempfile.mkdtemp("root")
        os.mkdir(os.path.join(repo_root, "config"))
        pom_template_path = self._write_file(repo_root, "WORKSPACE", "foo")
        pom_template_path = self._write_file(repo_root, "config/pom_template.xml", "foo")
        self._write_file(repo_root, ".pomgenrc", """
[artifact]
transitives_versioning_mode=counter
""")

        cfg = config.load(repo_root)

        self.assertEqual("counter", cfg.transitives_versioning_mode)

    def test_transitives_versioning_mode__invalid_value(self):
        repo_root = tempfile.mkdtemp("root")
        os.mkdir(os.path.join(repo_root, "config"))
        pom_template_path = self._write_file(repo_root, "WORKSPACE", "foo")
        pom_template_path = self._write_file(repo_root, "config/pom_template.xml", "foo")
        self._write_file(repo_root, ".pomgenrc", """
[artifact]
transitives_versioning_mode=foo
""")

        with self.assertRaises(Exception) as ctx:
            cfg = config.load(repo_root)

        self.assertIn("Invalid value", str(ctx.exception))
        self.assertIn("valid values are: ('semver', 'counter')", str(ctx.exception))

    def test_str(self):
        repo_root = tempfile.mkdtemp("root")
        pom_template_path = self._write_file(repo_root, "pom_template", "foo")
        ext_deps_p1 = self._write_file(repo_root, "ext_deps1", "abc")
        ext_deps_p2 = self._write_file(repo_root, "ext_deps2", "def")
        self._write_pomgenrc(repo_root, pom_template_path, "%s,%s" %
                             (ext_deps_p1, ext_deps_p2))

        cfg = config.load(repo_root)

        self.assertIn("pom_template_path=%s" % pom_template_path, str(cfg))
        self.assertIn("external_dependencies_path=%s,%s" % 
                      (ext_deps_p1, ext_deps_p2), str(cfg))

    def _write_pomgenrc(self, repo_root, pom_template_path, ext_deps_path):
        self._write_file(repo_root, ".pomgenrc", """[general]
external_dependencies_path=%s
pom_template_path=%s
""" % (ext_deps_path, pom_template_path))

    def _write_file(self, repo_root, relative_path, content):
        path = os.path.join(repo_root, relative_path)
        with open(path, "w") as f:
            f.write(content)
        return path

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
        

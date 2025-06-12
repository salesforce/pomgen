"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import os
import tempfile
import unittest


class MavenInstallTest(unittest.TestCase):

    def test_json_file_not_found(self):
        m = maveninstallinfo.MavenInstallInfo(("a/b/c", "d/e/f"))
        
        with self.assertRaises(Exception) as ctx:
            m.get_maven_install_names_and_paths("/repo_root")

        self.assertIn("not found", str(ctx.exception))
        self.assertIn("/repo_root/a/b/c", str(ctx.exception))

    def test_explicit_paths(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "my_rules_install.json")
        self._touch_file_at_path(repo_root, "tools/maven_install.json")
        m = maveninstallinfo.MavenInstallInfo(("my_rules_install.json", "tools/maven_install.json"))

        files = m.get_maven_install_names_and_paths(repo_root)

        self.assertEqual(2, len(files))
        self.assertEqual("my_rules", files[0][0])
        self.assertEqual(os.path.join(repo_root, "my_rules_install.json"), files[0][1])
        self.assertEqual("maven", files[1][0])
        self.assertEqual(os.path.join(repo_root, "tools", "maven_install.json"), files[1][1])

    def test_path_with_glob(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "tools/my_rules_install.json")
        self._touch_file_at_path(repo_root, "tools/maven_install.json")
        self._touch_file_at_path(repo_root, "tools/not_me")
        m = maveninstallinfo.MavenInstallInfo(("tools/*",))

        files = m.get_maven_install_names_and_paths(repo_root)

        self.assertEqual(2, len(files))
        self.assertEqual("maven", files[0][0])
        self.assertEqual(os.path.join(repo_root, "tools", "maven_install.json"), files[0][1])
        self.assertEqual("my_rules", files[1][0])
        self.assertEqual(os.path.join(repo_root, "tools", "my_rules_install.json"), files[1][1])

    def test_path_with_glob_and_exclusions(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "tools/my_rules_install.json")
        self._touch_file_at_path(repo_root, "tools/maven_install.json")
        self._touch_file_at_path(repo_root, "tools/maven_blah_install.json")
        m = maveninstallinfo.MavenInstallInfo(("tools/*", "-tools/maven_install.json",))

        files = m.get_maven_install_names_and_paths(repo_root)

        self.assertEqual(2, len(files))
        self.assertEqual("maven_blah", files[0][0])
        self.assertEqual(os.path.join(repo_root, "tools", "maven_blah_install.json"), files[0][1])
        self.assertEqual("my_rules", files[1][0])
        self.assertEqual(os.path.join(repo_root, "tools", "my_rules_install.json"), files[1][1])

    def _touch_file_at_path(self, repo_root_path, file_path):
        path = os.path.join(repo_root_path, file_path)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write("abc\n")


if __name__ == '__main__':
    unittest.main()

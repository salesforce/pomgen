"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import extdeps_pomgen
import os
import tempfile
import unittest

class ExtDepsPomgenTest(unittest.TestCase):

    def test1(self):
        self._setup_workspace()
        args = ("--repo_root", self.repo_root_path,)

        pom = extdeps_pomgen.main(args)

        self.assertIn("<groupId>com.google.guava</groupId>", pom)
        self.assertIn("<artifactId>guava</artifactId>", pom)
        self.assertIn("<version>23.0</version", pom)

    def _setup_workspace(self):
        self.repo_root_path = tempfile.mkdtemp("monorepo")
        self._add_WORKSPACE_file()
        self._add_pom_template()

    def _add_WORKSPACE_file(self):
        content = """
maven_jar(
    name = "com_google_guava_guava",
    artifact = "com.google.guava:guava:23.0",
)
"""
        self._write_file("", "", "WORKSPACE", content)

    def _add_pom_template(self):
        content = "${dependencies}"
        self._write_file("config", "", "pom_template.xml", content)

    def _write_file(self, package_rel_path, rel_path, filename, content):
        print(content)
        path = os.path.join(self.repo_root_path, package_rel_path, rel_path, 
                            filename)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(content)

if __name__ == '__main__':
    unittest.main()

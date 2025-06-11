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

    def test_extdeps_pomgens(self):
        self._setup_workspace()
        args = ("--repo_root", self.repo_root_path,)

        pom = extdeps_pomgen.main(args)

        self.assertIn("<groupId>com.google.guava</groupId>", pom)
        self.assertIn("<artifactId>guava</artifactId>", pom)
        self.assertIn("<version>23.0</version", pom)

        self.assertIn("<groupId>org.apache.commons</groupId>", pom)
        self.assertIn("<artifactId>commons-lang3</artifactId>", pom)
        self.assertIn("<version>3.9</version", pom)

        self.assertIn("<groupId>org.apache.commons</groupId>", pom)
        self.assertIn("<artifactId>commons-lang3</artifactId>", pom)
        self.assertIn("<version>3.9</version", pom)

        self.assertIn("<groupId>org.apache.commons</groupId>", pom)
        self.assertIn("<artifactId>commons-math3</artifactId>", pom)
        self.assertIn("<version>3.6.1</version", pom)

    def _setup_workspace(self):
        self.repo_root_path = tempfile.mkdtemp("monorepo")
        self._add_WORKSPACE_file()
        self._add_maven_install_json_file()
        self._add_pom_template()
        self._add_rc_file()

    def _add_WORKSPACE_file(self):
        self._write_file("", "", "WORKSPACE", "needs to exist")

    def _add_maven_install_json_file(self):
        content = """
{
    "artifacts": {
        "com.google.guava:guava": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "23.0"
        },
        "org.apache.commons:commons-lang3": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "3.9"
        },
        "org.apache.commons:commons-math3": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "3.6.1"
        }
    },
    "dependencies": {},
    "repositories": {
        "https://maven.google.com/": [
            "com.google.guava:guava",
            "org.apache.commons:commons-lang3",
            "org.apache.commons:commons-math3"
        ]
    },
    "version": "2"
}
        """
        self._write_file("", "", "maven_install.json", content)

    def _add_rc_file(self):
       self._write_file("","",".poppyrc", """
[general]
pom_template_path=pom_template.xml
maven_install_paths=maven_install.json
""")

    def _add_pom_template(self):
        content = "#{dependencies}"
        self._write_file("", "", "pom_template.xml", content)

    def _write_file(self, package_rel_path, rel_path, filename, content):
        path = os.path.join(self.repo_root_path, package_rel_path, rel_path, 
                            filename)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(content)

if __name__ == '__main__':
    unittest.main()

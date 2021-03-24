"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common.os_util import run_cmd
import os
import pomgen
import unittest
import tempfile

class PomGenTest(unittest.TestCase):
    """
    End-to-end pomgen blackbox functional tests.

    NOTE: consider running all tests here in the same workspace, so that bazel
    is only installed once.
    """

    def test_dynamic_pomgen(self):
        group_id = "g1"; artifact_id = "a1"; version = "1.0.0"
        self._setup_workspace()
        package_rel_path = "mypackage"
        self._add_package(package_rel_path, group_id, artifact_id, version)
        destdir = tempfile.mkdtemp("pomgen_dest")
        args = ["--package", package_rel_path, 
                "--destdir", destdir,
                "--repo_root", self.repo_root_path,]

        pomgen.main(args)

        pom_xml_path = os.path.join(destdir, package_rel_path, "pom.xml")
        content = self._read_file(pom_xml_path)
        self.assertIn("<groupId>g1</groupId>", content)
        self.assertIn("<artifactId>a1</artifactId>", content)
        self.assertIn("<version>1.0.0</version>", content)

    def _setup_workspace(self):
        self.repo_root_path = tempfile.mkdtemp("monorepo")
        self._add_WORKSPACE_file()
        self._add_pom_template()
        self._write_file("","","maven_install.json", """
{
    "dependency_tree": {
        "dependencies": []
    }
}
""")
        self._write_file("","",".bazelversion", "3.7.1")

    def _add_WORKSPACE_file(self):
        content = """
# too slow - check a couple of jar into the repo instead?
#maven_jar(
#    name = "com_google_guava_guava",
#    artifact = "com.google.guava:guava:23.0",
#)
"""
        self._write_file("", "", "WORKSPACE", content)

    def _add_pom_template(self):
        content = """
<project>
    <groupId>#{group_id}</groupId>
    <artifactId>#{artifact_id}</artifactId>
    <version>#{version}</version>
</project>
"""
        self._write_file("config", "", "pom_template.xml", content)

    def _add_package(self, package_rel_path, group_id, artifact_id, version):
        self._add_BUILD_file(package_rel_path)
        self._add_mvn_inf(package_rel_path, group_id, artifact_id, version)

    def _add_mvn_inf(self, package_rel_path, group_id, artifact_id, version):
        self._add_BUILD_pom_file(package_rel_path, group_id, artifact_id, version)
        self._add_LIBRARY_root(package_rel_path)

    def _add_BUILD_file(self, package_rel_path):
        content = """
java_library(
    name = "%s",
    #runtime_deps = ["@com_google_guava_guava//jar",],
)
"""
        target_name = os.path.basename(package_rel_path)
        self._write_file(package_rel_path, "", "BUILD", 
                         content % target_name) 

    def _add_BUILD_pom_file(self, package_rel_path, group_id, artifact_id,
                            version):
        content = """
maven_artifact(
    group_id = "%s",
    artifact_id = "%s",
    version = "%s",
    pom_generation_mode = "dynamic",
)

maven_artifact_update(
    version_increment_strategy = "minor"
)
"""
        content = content % (group_id, artifact_id, version)

        self._add_BUILD_pom_file_with_content(package_rel_path, content)

    def _add_BUILD_pom_file_with_content(self, package_rel_path, content):
        self._write_file(package_rel_path, "MVN-INF", "BUILD.pom", content)

    def _add_LIBRARY_root(self, package_rel_path):
        self._write_file(package_rel_path, "MVN-INF", "LIBRARY.root", "")

    def _write_file(self, package_rel_path, rel_path, filename, content):
        path = os.path.join(self.repo_root_path, package_rel_path, rel_path, 
                            filename)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(content)

    def _read_file(self, path):
        with open(path, "r") as f:
             return f.read()
        
if __name__ == '__main__':
    unittest.main()

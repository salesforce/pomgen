"""
Copyright (c) 2025, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import config.config as config
import common.manifestcontent as manifestcontent
import common.genmode as genmode
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import os
import tempfile
import unittest


class WorkspaceTest(unittest.TestCase):

    def setup_repository(self, cfg=None):
        """
        The state that all tests need.
        """
        if cfg is None:
            cfg = self._get_config()
        self.repo_root_path = tempfile.mkdtemp("root")
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root_path, cfg, manifestcontent.NOOP, verbose=True)
        self.ws = workspace.Workspace(self.repo_root_path, cfg, self.fac)

    def test_parse_maven_artifact_def(self):
        self.setup_repository()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1")

        art_def = self.ws.parse_maven_artifact_def("lib/a1")

        self.assertEqual(art_def.bazel_package, "lib/a1")
        self.assertEqual(art_def.version, "1.0.0-SNAPSHOT")
        self.assertIs(art_def.generation_mode, genmode.DYNAMIC)

    def test_parse_maven_artifact_def__version_in_lib_root(self):
        self.setup_repository()
        self._write_library_root(self.repo_root_path, "lib", version="96.0.0")
        self._add_artifact(self.repo_root_path, "lib/a1", version=None)

        art_def = self.ws.parse_maven_artifact_def("lib/a1")

        self.assertEqual("a1", art_def.artifact_id)
        self.assertEqual("lib/a1/MVN-INF/BUILD.pom", art_def.get_md_file_path_for_attr("artifact_id"))
        self.assertEqual(art_def.version, "96.0.0")        
        self.assertEqual("lib/MVN-INF/LIBRARY.root", art_def.get_md_file_path_for_attr("version"))

    def test_parse_child_package_without_art_def(self):
        self.setup_repository()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/src")

        parent_art_def = self.ws.parse_maven_artifact_def("lib/src")
        self.assertIs(parent_art_def.generation_mode, genmode.DYNAMIC)

        with self.assertRaises(Exception) as ctx:
            self.ws.parse_maven_artifact_def("lib/src/nothing", parent_art_def)
        self.assertIn("did not find any metadata at [lib/src/nothing], found parent metadata at [lib/src], however parent does not have required 1:1:1 mode enabled", str(ctx.exception))

    def test_parse_child_package_without_art_def_no_parent_either(self):
        self.setup_repository()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/src")
        art_def = self.ws.parse_maven_artifact_def("lib/src")

        art_dep = self.ws.parse_maven_artifact_def("lib/nothing", art_def)

        self.assertIsNone(art_dep)

    def test_parse_child_package_without_art_def__111(self):
        self.setup_repository()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/src",
                           generation_mode="dynamic_111")

        parent_art_def = self.ws.parse_maven_artifact_def("lib/src")
        self.assertIs(parent_art_def.generation_mode, genmode.DYNAMIC_ONEONEONE)

        art_def = self.ws.parse_maven_artifact_def("lib/src/a1", parent_art_def)
        self.assertIs(art_def.generation_mode, genmode.ONEONEONE_CHILD)

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)

    def _write_library_root(self, repo_root_path, package_rel_path, version=None):
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
            if version is None:
                f.write("")
            else:
                content = """
artifact(
    version = "%s",
)
""" % version
                f.write(content)

    def _add_artifact(self, repo_root_path, package_rel_path,
                      version="1.0.0-SNAPSHOT",
                      generation_mode="dynamic"):
        self._write_build_pom(repo_root_path, package_rel_path, 
                              artifact_id=os.path.basename(package_rel_path),
                              group_id="g1",
                              version=version,
                              generation_mode=generation_mode)

        self._write_build_file(repo_root_path, package_rel_path)

    def _write_build_pom(self, repo_root_path, package_rel_path,
                         artifact_id, group_id, version, generation_mode):

        version_content = "" if version is None else 'version = "%s",a' % version
        
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    %s
    generation_mode = "%s",
)

maven_artifact_update(
    version_increment_strategy = "patch"
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        os.makedirs(path)
        content = build_pom % (artifact_id, group_id, version_content, generation_mode)
                               
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
            f.write(content)

    def _write_build_file(self, repo_root_path, package_rel_path):
        name = os.path.basename(package_rel_path)

        build_file = """
java_library(
    name = "%s",
    srcs = ["%s.java"],
    visibility = ["//visibility:public"],
)
""" % (name, name)
        path = os.path.join(repo_root_path, package_rel_path)
        if not os.path.exists(path):
            os.makedirs(path)
        build_file_path = os.path.join(path, "BUILD")
        with open(build_file_path, "w") as f:
           f.write(build_file)


if __name__ == '__main__':
    unittest.main()

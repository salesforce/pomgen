"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import pomgenmode
from crawl import buildpom
import os
import tempfile
import unittest

class BuildPomTest(unittest.TestCase):

    def test_parse_BUILD_pom(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, "dynamic")

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertEqual(group_id, art_def.group_id)
        self.assertEqual(artifact_id, art_def.artifact_id)
        self.assertEqual(version, art_def.version)
        self.assertEqual([], art_def.deps)
        self.assertIs(pomgenmode.DYNAMIC, art_def.pom_generation_mode)
        self.assertEqual(None, art_def.pom_template_file)
        self.assertTrue(art_def.include_deps)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual(None, art_def.released_version)
        self.assertEqual(None, art_def.released_artifact_hash)
        self.assertIsNotNone(art_def.version_increment_strategy)

    def test_parse_BUILD_pom_and_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        released_version = "1.2.2"
        released_artifact_hash = "af5fe5cac7dfcfbc500283b111ea9e37083e5862"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, "dynamic")
        self._write_build_pom_released(repo_package, released_version, released_artifact_hash)

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertEqual(group_id, art_def.group_id)
        self.assertEqual(artifact_id, art_def.artifact_id)
        self.assertEqual(version, art_def.version)
        self.assertEqual([], art_def.deps)
        self.assertIs(pomgenmode.DYNAMIC, art_def.pom_generation_mode)
        self.assertEqual(None, art_def.pom_template_file)
        self.assertTrue(art_def.include_deps)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual(released_version, art_def.released_version)
        self.assertEqual(released_artifact_hash, art_def.released_artifact_hash)

    def test_parse_BUILD_pom__default_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode=None)

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertIs(pomgenmode.DYNAMIC, art_def.pom_generation_mode)

    def test_parse_BUILD_pom__dynamic_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode="dynamic")

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertIs(pomgenmode.DYNAMIC, art_def.pom_generation_mode)

    def test_parse_BUILD_pom__template_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode="template")

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertIs(pomgenmode.TEMPLATE, art_def.pom_generation_mode)

    def test_parse_BUILD_pom__skip_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom_skip_generation_mode(repo_package)

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        self.assertIs(pomgenmode.SKIP, art_def.pom_generation_mode)
        self.assertEqual(None, art_def.group_id)
        self.assertEqual(None, art_def.artifact_id)
        self.assertEqual(None, art_def.version)
        self.assertEqual([], art_def.deps)
        self.assertEqual(None, art_def.pom_template_file)
        self.assertTrue(art_def.include_deps)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual(None, art_def.released_version)
        self.assertEqual(None, art_def.released_artifact_hash)
        self.assertEqual(None, art_def.version_increment_strategy)

    def test_load_pom_xml_released(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, "dynamic")
        pom_content = self._write_pom_xml_released(repo_package)

        art_def = buildpom.parse_maven_artifact_def(repo_root, package_rel_path)

        # strip because loading the pom should also strip whitespace
        self.assertEqual(pom_content.strip(), art_def.released_pom_content)


    def _write_build_pom(self, package_path, artifact_id, group_id, version, pom_gen_mode):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    %s # pom_generation_mode
)

maven_artifact_update(
    version_increment_strategy = "major",
)
"""

        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
           f.write(build_pom % (artifact_id, group_id, version,
           ("" if pom_gen_mode is None else 'pom_generation_mode = "%s"' % pom_gen_mode)))

    def _write_build_pom_skip_generation_mode(self, package_path):
        build_pom = """
maven_artifact(
    pom_generation_mode = "skip",
)
"""
        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
           f.write(build_pom)

    def _write_build_pom_released(self, package_path, released_version, released_artifact_hash):
        build_pom_released = """
released_maven_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom.released"), "w") as f:
           f.write(build_pom_released % (released_version, released_artifact_hash))

    def _write_pom_xml_released(self, package_path):
        pom_content = "<this is a pom/>       "
        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "pom.xml.released"), "w") as f:
           f.write(pom_content)
        return pom_content

if __name__ == '__main__':
    unittest.main()

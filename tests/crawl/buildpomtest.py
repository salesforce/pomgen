"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import common.genmode as genmode
import config.config as config
import crawl.buildpom as buildpom
import common.manifestcontent as manifestcontent
import generate.impl.pom.dependencymd as dependencymd
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import generate.impl.pom.pomgenerationstrategy as pomgenerationstrategy
import os
import tempfile
import unittest


class BuildPomTest(unittest.TestCase):

    def test_parse_BUILD_pom(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "template",
                              include_deps=False,
                              deps = ["//a/b/c", "//d/e/f"])

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual(group_id, art_def.group_id)
        self.assertEqual(artifact_id, art_def.artifact_id)
        self.assertEqual(version, art_def.version)
        self.assertEqual(["//a/b/c", "//d/e/f"], art_def.deps)
        self.assertIs(genmode.TEMPLATE, art_def.generation_mode)
        self.assertEqual(None, art_def.custom_pom_template_content)
        self.assertFalse(art_def.include_deps)
        self.assertTrue(art_def.change_detection)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual("package2", art_def.bazel_target)
        self.assertEqual(None, art_def.released_version)
        self.assertEqual(None, art_def.released_artifact_hash)
        self.assertEqual("major", art_def.version_increment_strategy_name)
        self.assertEqual(None, art_def.jar_path)
        self.assertFalse(art_def.gen_dependency_management_pom)

    def test_parse_without_BUILD_pom(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)

        artifact_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        # TODO - can this throw an exception with a useful message?
        self.assertIsNone(artifact_def)

    def test_parse_BUILD__pom__empty_deps(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "template",
                              deps = [])

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual([], art_def.deps)

    def test_parse_BUILD_pom_gen_dep_man_pom(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)

        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "dynamic",
                              generate_dependency_management_pom=True)
        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())
        self.assertTrue(art_def.gen_dependency_management_pom)

        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "dynamic",
                              generate_dependency_management_pom=False)
        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())
        self.assertFalse(art_def.gen_dependency_management_pom)

    def test_parse_BUILD_pom_with_change_detection(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)

        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "dynamic",
                              change_detection=False)
        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())
        self.assertFalse(art_def.change_detection)

        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "dynamic",
                              change_detection=True)
        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())
        self.assertTrue(art_def.change_detection)

    def test_parse_BUILD_pom_and_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        released_version = "1.2.2"
        released_artifact_hash = "af5fe5cac7dfcfbc500283b111ea9e37083e5862"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, "dynamic")
        self._write_build_pom_released(repo_package, released_version, released_artifact_hash)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual(group_id, art_def.group_id)
        self.assertEqual(artifact_id, art_def.artifact_id)
        self.assertEqual(version, art_def.version)
        self.assertEqual([], art_def.deps)
        self.assertIs(genmode.DYNAMIC, art_def.generation_mode)
        self.assertEqual(None, art_def.custom_pom_template_content)
        self.assertTrue(art_def.include_deps)
        self.assertTrue(art_def.change_detection)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual(released_version, art_def.released_version)
        self.assertEqual(released_artifact_hash, art_def.released_artifact_hash)

    def test_parse_BUILD_pom__default_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode="dynamic")

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertIs(genmode.DYNAMIC, art_def.generation_mode)

    def test_parse_BUILD_pom__dynamic_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode="dynamic")

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertIs(genmode.DYNAMIC, art_def.generation_mode)
        self.assertTrue(art_def.generation_mode.produces_artifact)

    def test_parse_BUILD_pom__template_pomgen_mode(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, pom_gen_mode="template")

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertIs(genmode.TEMPLATE, art_def.generation_mode)
        self.assertTrue(art_def.generation_mode.produces_artifact)

    def test_parse_BUILD_pom__additional_change_detected_packages(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        more_packages = ["//root/a/b/c", "root/d/e/f"]
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(
            repo_package, artifact_id, group_id, version,
            pom_gen_mode="template",
            additional_change_detected_packages=more_packages)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual(art_def.additional_change_detected_packages, ["root/a/b/c", "root/d/e/f"])

    def test_parse_BUILD_pom__skip_pomgen_mode(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom_skip_generation_mode(repo_package)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertIs(genmode.SKIP, art_def.generation_mode)
        self.assertEqual(None, art_def.group_id)
        self.assertEqual(None, art_def.artifact_id)
        self.assertEqual(None, art_def.version)
        self.assertEqual([], art_def.deps)
        self.assertEqual(None, art_def.custom_pom_template_content)
        self.assertTrue(art_def.include_deps)
        self.assertTrue(art_def.change_detection)
        self.assertEqual(package_rel_path, art_def.bazel_package)
        self.assertEqual(None, art_def.released_version)
        self.assertEqual(None, art_def.released_artifact_hash)
        self.assertEqual(None, art_def.version_increment_strategy_name)
        self.assertFalse(art_def.generation_mode.produces_artifact)

    def test_parse_BUILD_pom__jar_path(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        jar_path = "../a-jar.jar"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              pom_gen_mode="template",
                              jar_path=jar_path)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual("package1/package2/a-jar.jar", art_def.jar_path)

    def test_parse_BUILD_pom__custom_target(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        target = "juicer_lib"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              pom_gen_mode="template",
                              bazel_target=target)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        self.assertEqual(target, art_def.bazel_target)

    def test_load_pom_xml_released(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version, "dynamic")
        pom_content = self._write_pom_xml_released(repo_package)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        # strip because loading the pom strips trailing whitespace
        self.assertEqual(pom_content.strip(), art_def.released_pom_content)

    def test_load_custom_pom_template(self):
        package_rel_path = "package1/package2"
        group_id = "group1"
        artifact_id = "art1"
        version = "1.2.3"
        repo_root = tempfile.mkdtemp("reporoot")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, artifact_id, group_id, version,
                              "template",
                              pom_template_file="pom.template")
        template_content = self._write_pom_template(repo_package)

        art_def = buildpom.parse_maven_artifact_def(
            repo_root, package_rel_path, self._get_strategy())

        # strip because loading the template strips trailing whitespace
        self.assertEqual(template_content.strip(), art_def.custom_pom_template_content)

    def test_is_or_has_same_111_parent(self):
        parent_art_def = buildpom.MavenArtifactDef(
            "pg", "pa", "1", generation_mode=genmode.DYNAMIC_ONEONEONE)
        other_parent_art_def = buildpom.MavenArtifactDef(
            "pg2", "pa2", "1", generation_mode=genmode.DYNAMIC_ONEONEONE)
        art_def = buildpom.MavenArtifactDef(
            "g", "a", "1", generation_mode=genmode.ONEONEONE_CHILD,
            parent_artifact_def=parent_art_def)
        art_def_with_same_parent = buildpom.MavenArtifactDef(
            "g2", "a2", "1", generation_mode=genmode.ONEONEONE_CHILD,
            parent_artifact_def=parent_art_def)
        art_def_with_other_parent = buildpom.MavenArtifactDef(
            "g2", "a2", "1", generation_mode=genmode.ONEONEONE_CHILD,
            parent_artifact_def=other_parent_art_def)

        self.assertTrue(art_def.is_or_has_same_111_parent(parent_art_def))
        self.assertTrue(art_def.is_or_has_same_111_parent(art_def_with_same_parent))
        self.assertFalse(art_def.is_or_has_same_111_parent(art_def_with_other_parent))

    def _write_build_pom(self,
                         package_path,
                         artifact_id,
                         group_id, version,
                         pom_gen_mode,
                         include_deps=None,
                         change_detection=None,
                         additional_change_detected_packages=None,
                         deps=None,
                         jar_path=None,
                         pom_template_file=None,
                         bazel_target=None,
                         generate_dependency_management_pom=None):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    generation_mode = '%s',
    %s
    %s
    %s
    %s
    %s
    %s
    %s
    %s
)

maven_artifact_update(
    version_increment_strategy = "major",
)
""" % (artifact_id, group_id, version, pom_gen_mode,
       "" if include_deps is None else "include_deps = %s," % include_deps,
       "" if change_detection is None else "change_detection = %s," % change_detection,
       "" if additional_change_detected_packages is None else "additional_change_detected_packages = %s," % additional_change_detected_packages,
       "" if deps is None else "deps = %s," % deps,
       "" if jar_path is None else 'jar_path = "%s",' % jar_path,
       "" if pom_template_file is None else 'pom_template_file = "%s",' % pom_template_file,
       "" if bazel_target is None else 'target_name = "%s",' % bazel_target,
       "" if generate_dependency_management_pom is None else 'generate_dependency_management_pom = %s,' % generate_dependency_management_pom)

        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
           f.write(build_pom)

    def _write_build_pom_skip_generation_mode(self, package_path):
        build_pom = """
maven_artifact(
    generation_mode = "skip",
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

    def _write_pom_template(self, package_path):
        template_content = "<this is a pom template/>       "
        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "pom.template"), "w") as f:
           f.write(template_content)
        return template_content

    def _get_strategy(self):
        strategy = pomgenerationstrategy.PomGenerationStrategy(
            "root", config.Config(), maveninstallinfo.NOOP,
            dependencymd.DependencyMetadata(None),
            manifestcontent.NOOP, label_to_overridden_fq_label={}, verbose=True)
        strategy.initialize()
        return strategy


if __name__ == '__main__':
    unittest.main()

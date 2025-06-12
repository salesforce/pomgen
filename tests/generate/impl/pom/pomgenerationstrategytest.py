"""
Copyright (c) 2025, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import common.label as labelm
import common.os_util as os_util
import config.config as config
import config.exclusions as exclusions
import crawl.git as git
import crawl.pomcontent as pomcontent
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import generate.impl.pom.dependency as dependency
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import generate.impl.pom.maveninstallparser as maveninstallparser
import os
import tempfile
import unittest


class PomGenerationStrategyTest(unittest.TestCase):

    def setUp(self):
        self._org_parse_func = maveninstallparser.parse_maven_install
        f = dependency.new_dep_from_maven_art_str
        query_result = [
            (f("org.apache.maven:maven-artifact:3.3.9", "maven"), [],),
            (f("com.google.guava:guava:23.0", "maven"), [],),
            (f("ch.qos.logback:logback-classic:1.2.3", "maven"), [],)
        ]
        maveninstallparser.parse_maven_install = lambda names, paths, verbose: query_result

        self.repo_root = tempfile.mkdtemp("root")
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root, _get_config(), pomcontent.NOOP, verbose=True)
        self.ws = workspace.Workspace(self.repo_root, _get_config(), self.fac)
    
    def tearDown(self):
        maveninstallparser.parse_maven_install = self._org_parse_func

    def test_parse_src_dep(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance.
        """
        artifact_version = "1.2.3"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        _touch_file_at_path(self.repo_root, "", "MVN-INF", "LIBRARY.root")
        _write_build_pom(self.repo_root, package_name, artifact_id, group_id, artifact_version)
        artifact_def = self.ws.parse_maven_artifact_def(package_name)

        label = labelm.Label("//%s" % package_name)
        dep = self.fac._pomstrategy.load_dependency(label, artifact_def)

        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)
        self.assertEqual(artifact_version, dep.version)
        self.assertFalse(dep.external)
        self.assertEqual(package_name, dep.bazel_package)
        self.assertIsNone(dep.classifier)

    def test_parse_src_dep_with_target(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance, when the source dependency includes a target
        """
        artifact_version = "1.2.3"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        _touch_file_at_path(self.repo_root, "", "MVN-INF", "LIBRARY.root")
        _write_build_pom(self.repo_root, package_name, artifact_id, group_id, artifact_version)
        artifact_def = self.ws.parse_maven_artifact_def(package_name)

        label = labelm.Label("//%s:target_name" % package_name)
        dep = self.fac._pomstrategy.load_dependency(label, artifact_def)

        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)
        self.assertEqual(artifact_version, dep.version)
        self.assertFalse(dep.external)
        self.assertEqual(package_name, dep.bazel_package)
        self.assertIsNone(dep.classifier)

    def test_parse_ext_dep(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance.
        """
        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")
        dep = self.fac._pomstrategy.load_dependency(label, None)

        self.assertEqual("ch.qos.logback", dep.group_id)
        self.assertEqual("logback-classic", dep.artifact_id)
        self.assertEqual("1.2.3", dep.version)
        self.assertTrue(dep.external)
        self.assertIsNone(dep.bazel_package)

    def test_parse_ext_dep__unknown_dep(self):
        """
        Verifies the error that is thrown when an unknown dep is encountered.
        """
        label = labelm.Label("@maven//:bad_bad_bad_qos_logback_logback_classic")

        with self.assertRaises(Exception) as ctx:
            self.fac._pomstrategy.load_dependency(label, None)
        self.assertIn("json files have been registered", str(ctx.exception))
        self.assertIn("maven_install_paths in the pomgen config file", str(ctx.exception))

    def test_parse_ext_dep_with_reserved_words(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance when the strings being parsed contain reserved words
        such as "artifact".
        """
        label = labelm.Label("@maven//:org_apache_maven_maven_artifact")
        dep = self.fac._pomstrategy.load_dependency(label, None)

        self.assertEqual("org.apache.maven", dep.group_id)
        self.assertEqual("maven-artifact", dep.artifact_id)
        self.assertEqual("3.3.9", dep.version)

    def test_parse_src_dep_without_changes_since_last_release(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance.

        The source dependency has a BUILD.pom.released file that indicates
        that no changes have been made since the last release; therefore
        the dependency instance should point to the previously released 
        artifact.
        """
        version = "1.2.3"
        released_version = "1.2.0"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        _touch_file_at_path(self.repo_root, "", "MVN-INF", "LIBRARY.root")
        _write_build_pom(self.repo_root, package_name, artifact_id, group_id, version)
        _setup_repo(self.repo_root)
        package_hash = git.get_dir_hash(self.repo_root, [package_name], exclusions.src_exclusions())
        _write_build_pom_released(self.repo_root, package_name, released_version, package_hash)
        artifact_def = self.ws.parse_maven_artifact_def(package_name)

        label = labelm.Label("//%s" % package_name)
        dep = self.fac._pomstrategy.load_dependency(label, artifact_def)

        self.assertIsNotNone(dep)
        self.assertEqual(released_version, dep.version) # <-- prev rel version
        self.assertTrue(dep.external) # <-- external == previously uploaded
        self.assertEqual(package_name, dep.bazel_package)
        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)

    def test_parse_src_dep_with_changes_since_last_release(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance.

        The source dependency has a BUILD.pom.released file that indicates
        that changes have been made since the last release; therefore
        the dependency instance should point to the monorepo source artifact.
        """
        version = "1.2.3"
        released_version = "1.2.0"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        _touch_file_at_path(self.repo_root, "", "MVN-INF", "LIBRARY.root")
        _write_build_pom(self.repo_root, package_name, artifact_id, group_id, version)
        _setup_repo(self.repo_root)
        package_hash = git.get_dir_hash(self.repo_root, [package_name], exclusions.src_exclusions())
        _write_build_pom_released(self.repo_root, package_name, released_version, package_hash)
        _touch_file_at_path(self.repo_root, package_name, "", "myfile")
        _commit(self.repo_root)
        artifact_def = self.ws.parse_maven_artifact_def(package_name)

        label = labelm.Label("//%s" % package_name)
        dep = self.fac._pomstrategy.load_dependency(label, artifact_def)

        self.assertIsNotNone(dep)
        self.assertEqual(version, dep.version) # <-- current version
        self.assertFalse(dep.external) # <-- not external, built internally
        self.assertEqual(package_name, dep.bazel_package)
        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)


def _touch_file_at_path(repo_root_path, package_rel_path, within_package_rel_path, filename):
    path = os.path.join(repo_root_path, package_rel_path, within_package_rel_path, filename)
    if os.path.exists(path):
        with open(path, "r+") as f:
            content = f.read()
            content += "abc\n"
            f.seek(0)
            f.write(content)
            f.truncate()
    else:
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write("abc\n")


def _write_build_pom(repo_root_path, package_rel_path, artifact_id, group_id, version):
    build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "dynamic",
)

maven_artifact_update(
    version_increment_strategy = "minor",
)
"""
    path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
    os.makedirs(path)
    with open(os.path.join(path, "BUILD.pom"), "w") as f:
        f.write(build_pom % (artifact_id, group_id, version))


def _write_build_pom_released(repo_root_path, package_rel_path, released_version, released_artifact_hash):
    build_pom_released = """
released_maven_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
    path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, "BUILD.pom.released"), "w") as f:
       f.write(build_pom_released % (released_version, released_artifact_hash))


def _mocked_mvn_install_info(maven_install_name):
    mii = maveninstallinfo.MavenInstallInfo(())
    mii.get_maven_install_names_and_paths = lambda r: [(maven_install_name, "some/repo/path",)]
    return mii


def _get_config(**kwargs):
    return config.Config(**kwargs)


def _setup_repo(repo_root_path):
    os_util.run_cmd("git init .", cwd=repo_root_path)
    os_util.run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
    os_util.run_cmd("git config user.name 'test example'", cwd=repo_root_path)
    _commit(repo_root_path)


def _commit(repo_root_path):
    os_util.run_cmd("git add .", cwd=repo_root_path)
    os_util.run_cmd("git commit -m 'test commit'", cwd=repo_root_path)


if __name__ == '__main__':
    unittest.main()

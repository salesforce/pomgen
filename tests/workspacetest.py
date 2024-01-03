"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common.os_util import run_cmd
from common import maveninstallinfo
from common import pomgenmode
from config import config
from config import exclusions
from crawl import bazel
from crawl import buildpom
from crawl import dependency
from crawl import dependencymd as dependencym
from crawl import git
from crawl import pomcontent
from crawl import workspace
import os
import tempfile
import unittest


class WorkspaceTest(unittest.TestCase):

    def setUp(self):
        self.orig_bazel_parse_maven_install = bazel.parse_maven_install
        f = dependency.new_dep_from_maven_art_str
        query_result = [
            (f("org.apache.maven:maven-artifact:3.3.9", "maven"), [],),
            (f("com.google.guava:guava:23.0", "maven"), [],),
            (f("ch.qos.logback:logback-classic:1.2.3", "maven"), [],)
        ]
        bazel.parse_maven_install = lambda name, path: query_result
    
    def tearDown(self):
        bazel.parse_maven_install = self.orig_bazel_parse_maven_install

    def test_normalize_deps__default_removes_refs_to_same_package(self):
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("so/path",
                                 self._get_config(),
                                 maveninstallinfo.NOOP, 
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})
        package = "a/b/c"
        art1 = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                         pom_generation_mode=pomgenmode.DYNAMIC)
        dep1 = dependency.MonorepoDependency(art1, bazel_target=None)
        art2 = buildpom.MavenArtifactDef("g2", "a2", "1", bazel_package=package)
        dep2 = dependency.MonorepoDependency(art2, bazel_target=None)
        art3 = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package="d/e/f")
        dep3 = dependency.MonorepoDependency(art3, bazel_target=None)
        dep4 = dependency.ThirdPartyDependency("name", "g101", "a101", "1")

        # the result of this method is based on bazel_package comparison
        deps = ws.normalize_deps(art1, [dep1, dep2, dep3, dep4])

        self.assertEqual([dep3, dep4], deps)

    def test_normalize_deps__skip_pomgen_mode_allows_refs_to_same_package(self):
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("so/path",
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})
        package = "a/b/c"
        art1 = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                         pom_generation_mode=pomgenmode.SKIP)
        dep1 = dependency.MonorepoDependency(art1, bazel_target=None)
        art2 = buildpom.MavenArtifactDef("g2", "a2", "1", bazel_package=package)
        dep2 = dependency.MonorepoDependency(art2, bazel_target=None)
        art3 = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package="d/e/f")
        dep3 = dependency.MonorepoDependency(art3, bazel_target=None)
        dep4 = dependency.ThirdPartyDependency("name", "g101", "a101", "1")

        # the result of this method is based on bazel_package comparison
        deps = ws.normalize_deps(art1, [dep1, dep2, dep3, dep4])

        self.assertEqual([dep1, dep2, dep3, dep4], deps)

    def test_parse_ext_dep(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance.
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
                                 self._get_config(),
                                 maven_install_info=self._mocked_mvn_install_info("maven"),
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["@maven//:ch_qos_logback_logback_classic"])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.2.3", deps[0].version)
        self.assertTrue(deps[0].external)
        self.assertIsNone(deps[0].bazel_package)

    def test_parse_ext_dep__unknown_dep(self):
        """
        Verifies the error that is thrown when an unknown dep is encountered.
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
                                 self._get_config(),
                                 maven_install_info=self._mocked_mvn_install_info("maven"),
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        with self.assertRaises(Exception) as ctx:
            deps = ws.parse_dep_labels(["@maven//:bad_qos_logback_logback_classic"])
        self.assertIn("json files have been registered", str(ctx.exception))
        self.assertIn("maven_install_paths in the pomgen config file", str(ctx.exception))

    def test_excluded_dependency_paths(self):
        """
        Verifies that excluded dependency paths are not added to the list of 
        dependencies.
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
            config=self._get_config(excluded_dependency_paths=["projects/protos/",]),
            maven_install_info=self._mocked_mvn_install_info("maven"),
            pom_content=pomcontent.NOOP,
            dependency_metadata=depmd,
            label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["@maven//:ch_qos_logback_logback_classic", "//projects/protos/grail:java_protos"])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.2.3", deps[0].version)
        self.assertIsNone(deps[0].bazel_package)

    def test_excluded_dependency_labels(self):
        """
        Verifies that excluded dependency labels are not added to the list of 
        dependencies.
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
            config=self._get_config(excluded_dependency_labels=["@maven//:ch_qos_logback_logback_classic",]),
            maven_install_info=self._mocked_mvn_install_info("maven"),
            pom_content=pomcontent.NOOP,
            dependency_metadata=depmd,
            label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["@maven//:ch_qos_logback_logback_classic"])

        self.assertEqual(0, len(deps))
        
    def test_parse_ext_dep_with_reserved_words(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance when the strings being parsed contain reserved words
        such as "artifact".
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
                                 self._get_config(),
                                 maven_install_info=self._mocked_mvn_install_info("maven"),
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["@maven//:org_apache_maven_maven_artifact"])

        self.assertEqual(1, len(deps))
        self.assertEqual("org.apache.maven", deps[0].group_id)
        self.assertEqual("maven-artifact", deps[0].artifact_id)
        self.assertEqual("3.3.9", deps[0].version)

    def test_parse_src_dep(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance.
        """
        artifact_version = "1.2.3"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, artifact_version)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["//%s" % package_name])

        self.assertEqual(1, len(deps))
        self.assertEqual(group_id, deps[0].group_id)
        self.assertEqual(artifact_id, deps[0].artifact_id)
        self.assertEqual(artifact_version, deps[0].version)
        self.assertFalse(deps[0].external)
        self.assertEqual(package_name, deps[0].bazel_package)

    def test_parse_src_dep_with_target(self):
        """
        Verifies that a source dependency label is correctly parsed into a 
        Dependency instance, when the source dependency includes a target
        """
        artifact_version = "1.2.3"
        package_name = "package1"
        group_id = "group1"
        artifact_id = "art1"
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, artifact_version)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["//%s:my_cool_target" % package_name])

        self.assertEqual(1, len(deps))
        self.assertEqual(group_id, deps[0].group_id)
        self.assertEqual(artifact_id, deps[0].artifact_id)
        self.assertEqual(artifact_version, deps[0].version)
        self.assertFalse(deps[0].external)
        self.assertEqual(package_name, deps[0].bazel_package)
        self.assertEqual("my_cool_target", deps[0].bazel_target)
        self.assertIsNone(deps[0].classifier)

    def test_src_dep_without_build_pom(self):
        """
        Verifies we correctly produce an error when a monorepo src ref is 
        missing a BUILD.pom file.
        """
        artifact_version = "1.2.3"
        package_name = "package"
        group_id = "group1"
        artifact_id = "art1"
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, artifact_version)
        bad_package_name = "lombok"
        os.mkdir(os.path.join(repo_root, bad_package_name)) # no BUILD.pom
        self._write_basic_workspace_file(repo_root)
        self._write_build_file(repo_root, bad_package_name)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        with self.assertRaises(Exception) as ctx:
            deps = ws.parse_dep_labels(["//%s" % package_name,
                                        "//%s:%s" % (bad_package_name, bad_package_name)])

        self.assertIn("no BUILD.pom", str(ctx.exception))
        self.assertIn(bad_package_name, str(ctx.exception))

    def test_src_dep_with_neverlink_enabled(self):
        """
        Verifies that no error is triggered when a dep has neverlink enabled and it has no BUILD.pom file.
        """
        artifact_version = "1.2.3"
        package_name = "package"
        group_id = "group1"
        artifact_id = "art1"
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, artifact_version)
        bad_package_name = "lombok"
        os.mkdir(os.path.join(repo_root, bad_package_name)) # no BUILD.pom
        self._write_basic_workspace_file(repo_root)
        self._write_build_file(repo_root, bad_package_name, True)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["//%s" % package_name,
                                    "//%s:%s" % (bad_package_name, bad_package_name)])

        self.assertEqual(1, len(deps))

    def test_parse_invalid_dep(self):
        """
        Verifies that parsing of an invalid label behaves as expected.
        """
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace("some/path",
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        with self.assertRaises(Exception) as ctx:
            deps = ws.parse_dep_labels(["this is a label"])

        self.assertIn("bad label", str(ctx.exception))
        self.assertIn("this is a label", str(ctx.exception))

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
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, version)
        self._setup_repo(repo_root)
        package_hash = git.get_dir_hash(repo_root, [package_name], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root, package_name, released_version, package_hash)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["//%s" % package_name])

        self.assertEqual(1, len(deps))
        self.assertEqual(group_id, deps[0].group_id)
        self.assertEqual(artifact_id, deps[0].artifact_id)
        self.assertTrue(deps[0].external)
        self.assertEqual(released_version, deps[0].version)
        self.assertEqual(package_name, deps[0].bazel_package)

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
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self._write_build_pom(repo_root, package_name, artifact_id, group_id, version)
        self._setup_repo(repo_root)
        package_hash = git.get_dir_hash(repo_root, [package_name], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root, package_name, released_version, package_hash)
        self._touch_file_at_path(repo_root, package_name, "", "myfile")
        self._commit(repo_root)
        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})

        deps = ws.parse_dep_labels(["//%s" % package_name])

        self.assertEqual(1, len(deps))
        self.assertEqual(group_id, deps[0].group_id)
        self.assertEqual(artifact_id, deps[0].artifact_id)
        self.assertFalse(deps[0].external)
        self.assertEqual(version, deps[0].version)
        self.assertEqual(package_name, deps[0].bazel_package)

    def _setup_repo(self, repo_root_path):
        run_cmd("git init .", cwd=repo_root_path)
        run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        self._commit(repo_root_path)

    def _commit(self, repo_root_path):
        run_cmd("git add .", cwd=repo_root_path)
        run_cmd("git commit -m 'test commit'", cwd=repo_root_path)

    def _touch_file_at_path(self, repo_root_path, package_rel_path, within_package_rel_path, filename):
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

    def _write_build_pom(self, repo_root_path, package_rel_path, artifact_id, group_id, version):
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

    def _write_build_pom_released(self, repo_root_path, package_rel_path, released_version, released_artifact_hash):
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

    def _mocked_mvn_install_info(self, maven_install_name):
        mii = maveninstallinfo.MavenInstallInfo(())
        mii.get_maven_install_names_and_paths = lambda r: [(maven_install_name, "some/repo/path",)]
        return mii

    def _write_build_file(self, repo_root_path, package_rel_path, neverlink_attr_enabled = False):
        build_file = """
java_plugin(
    name = "lombok-plugin",
    generates_api = True,
    processor_class = "lombok.launch.AnnotationProcessorHider$AnnotationProcessor",
    visibility = ["//visibility:private"],
    deps = ["@nexus//:org_projectlombok_lombok"],
)

java_library(
    name = "lombok",
    neverlink = %s,
    exports = ["@nexus//:org_projectlombok_lombok"],
    exported_plugins = [":lombok-plugin"],
    visibility = ["//visibility:public"],
)
""" % (0 if neverlink_attr_enabled == False else 1)

        path = os.path.join(repo_root_path, package_rel_path)
        if not os.path.exists(path):
            os.makedirs(path)
        build_file_path = os.path.join(path, "BUILD")
        with open(build_file_path, "w") as f:
           f.write(build_file)

    def _write_basic_workspace_file(self, repo_root_path):
        workspace_file = """
workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "4.1"
RULES_JVM_EXTERNAL_SHA = "f36441aa876c4f6427bfb2d1f2d723b48e9d930b62662bf723ddfb8fc80f0140"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
    url = "https://github.com/bazelbuild/rules_jvm_external/archive/%s.zip" % RULES_JVM_EXTERNAL_TAG,
)

load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven")


load("@rules_jvm_external//:repositories.bzl", "rules_jvm_external_deps")
rules_jvm_external_deps()
load("@rules_jvm_external//:setup.bzl", "rules_jvm_external_setup")
rules_jvm_external_setup()
"""
        path = os.path.join(repo_root_path)
        if not os.path.exists(path):
            os.makedirs(path)
        workspace_file_path = os.path.join(path, "WORKSPACE")
        with open(workspace_file_path, "w") as f:
           f.write(workspace_file)

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)


if __name__ == '__main__':
    unittest.main()

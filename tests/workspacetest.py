"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common.os_util import run_cmd
from common import pomgenmode
from config import exclusions
from crawl import git
from crawl import buildpom
from crawl import dependency
from crawl import workspace
import os
import tempfile
import unittest

class WorkspaceTest(unittest.TestCase):

    def test_normalize_deps__default_removes_refs_to_same_package(self):
        ws = workspace.Workspace("so/path", "", [], exclusions.src_exclusions())
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
        ws = workspace.Workspace("so/path", "", [], exclusions.src_exclusions())
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
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4",
            )""", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@ch_qos_logback_logback_classic//jar"])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.4.4", deps[0].version)
        self.assertTrue(deps[0].external)
        self.assertIsNone(deps[0].bazel_package)

    def test_parse_excluded_ext_dep(self):
        """
        Verifies that a label for an exluced external dependency is skipped
        as expected
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4",
            )""", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@ch_qos_logback_logback_classic//jar",
                                    "@com_google_api_grpc_proto_google_common_protos//jar",])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.4.4", deps[0].version)
        self.assertTrue(deps[0].external)
        self.assertIsNone(deps[0].bazel_package)

    def test_parse_ext_dep__single_quotes(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance - test parsing with single-quote delimited strings.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = 'ch_qos_logback_logback_classic',
                artifact = 'ch.qos.logback:logback-classic:1.4.4',
            )""", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@ch_qos_logback_logback_classic//jar"])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.4.4", deps[0].version)
        self.assertTrue(deps[0].external)
        self.assertIsNone(deps[0].bazel_package)

    def test_parse_ext_dep__mixed_quotes(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance - test parsing with single-quote delimited strings.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = 'ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4',
            )""", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@ch_qos_logback_logback_classic//jar"])

        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.4.4", deps[0].version)
        self.assertTrue(deps[0].external)
        self.assertIsNone(deps[0].bazel_package)

    def test_parse_and_exclude_proto_labels(self):
        """
        Verifies that proto labels are ignored and not added to the list of dependencies
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = 'ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4',
            )""", 
            excluded_dependency_paths=["projects/protos/",], 
            source_exclusions=exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@ch_qos_logback_logback_classic//jar", "//projects/protos/grail:java_protos"])
        self.assertEqual(1, len(deps))
        self.assertEqual("ch.qos.logback", deps[0].group_id)
        self.assertEqual("logback-classic", deps[0].artifact_id)
        self.assertEqual("1.4.4", deps[0].version)
        self.assertIsNone(deps[0].bazel_package)
        
    def test_parse_ext_dep_with_reserved_words(self):
        """
        Verifies that an external dependency label is correctly parsed into a 
        Dependency instance when the strings being parsed contain reserved words
        such as "artifact".
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "org_apache_maven_maven_artifact",
                artifact = "org.apache.maven:maven-artifact:3.3.9",
            )""", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["@org_apache_maven_maven_artifact//jar"])

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
        ws = workspace.Workspace(repo_root, "", [], exclusions.src_exclusions())

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
        ws = workspace.Workspace(repo_root, "", [], exclusions.src_exclusions())

        deps = ws.parse_dep_labels(["//%s:my_cool_target" % package_name])

        self.assertEqual(1, len(deps))
        self.assertEqual(group_id, deps[0].group_id)
        self.assertEqual(artifact_id, deps[0].artifact_id)
        self.assertEqual(artifact_version, deps[0].version)
        self.assertFalse(deps[0].external)
        self.assertEqual(package_name, deps[0].bazel_package)
        self.assertEqual("my_cool_target", deps[0].bazel_target)

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
        bad_package_name = "bad_package"
        os.mkdir(os.path.join(repo_root, bad_package_name)) # no BUILD.pom

        ws = workspace.Workspace(repo_root, "", [], exclusions.src_exclusions())

        with self.assertRaises(Exception) as ctx:
            deps = ws.parse_dep_labels(["//%s" % package_name,
                                        "//%s" % bad_package_name])

        self.assertIn("no BUILD.pom", str(ctx.exception))
        self.assertIn(bad_package_name, str(ctx.exception))

    def test_parse_invalid_dep(self):
        """
        Verifies that parsing of an invalid label behaves as expected.
        """
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())

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
        package_hash = git.get_dir_hash(repo_root, package_name, exclusions.src_exclusions())
        self._write_build_pom_released(repo_root, package_name, released_version, package_hash)
        ws = workspace.Workspace(repo_root, "", [], exclusions.src_exclusions())

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
        package_hash = git.get_dir_hash(repo_root, package_name, exclusions.src_exclusions())
        self._write_build_pom_released(repo_root, package_name, released_version, package_hash)
        self._touch_file_at_path(repo_root, package_name, "", "myfile")
        self._commit(repo_root)
        ws = workspace.Workspace(repo_root, "", [], exclusions.src_exclusions())

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

if __name__ == '__main__':
    unittest.main()

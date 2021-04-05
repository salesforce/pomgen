"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import git
from common.os_util import run_cmd
from config import exclusions
from update import buildpomupdate
import os
import tempfile
import unittest
import subprocess

class BuildPomUpdateTest(unittest.TestCase):

    def test_update_BUILD_pom_released__set_artifact_hash_to_current(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(os.path.join(pack1_path))
        pack2_path = os.path.join(repo_root, pack2)
        os.makedirs(os.path.join(pack2_path))
        self._write_build_pom_released(pack1_path, "1.0.0", "aaa")
        self._write_build_pom_released(pack2_path, "1.0.0", "bbb")
        self._setup_repo(repo_root)
        self._commit(repo_root)
        self._touch_file_at_path(repo_root, pack1, "blah1")
        self._commit(repo_root)
        pack1_hash = git.get_dir_hash(repo_root, pack1, exclusions.src_exclusions())
        self._touch_file_at_path(repo_root, pack2, "blah2")
        self._commit(repo_root)
        pack2_hash = git.get_dir_hash(repo_root, pack2, exclusions.src_exclusions())
        self.assertNotEqual(pack1_hash, pack2_hash)
        
        buildpomupdate.update_released_artifact(repo_root, [pack1, pack2], exclusions.src_exclusions(), use_current_artifact_hash=True)

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack1_hash, content)
        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack2_hash, content)

    def test_update_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom_released(repo_package, "1.0.0", "aaa")
        # sanity:
        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('version = "1.0.0"', content)
            self.assertIn('artifact_hash = "aaa"', content)

        buildpomupdate.update_released_artifact(repo_root, [package_rel_path], exclusions.src_exclusions(), "1.2.3", "abc")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('released_maven_artifact(', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn('artifact_hash = "abc"', content)

    def test_create_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)

        buildpomupdate.update_released_artifact(repo_root, [package_rel_path], exclusions.src_exclusions(), "1.2.3", "abc")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('released_maven_artifact(', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn('artifact_hash = "abc"', content)

    def test_get_build_pom_released_content(self):
        expected_content = """released_maven_artifact(
    version = "1.0.0",
    artifact_hash = "abcdefghi",
)
"""
        self.assertEqual(expected_content, buildpomupdate._get_build_pom_released_content("1.0.0", "abcdefghi"))

    def test_update_released_artifact_hash(self):
        content = """
released_maven_artifact(
    artifact_hash = "123456789",
    version = "1.0.0",
)
"""
        expected_content = """
released_maven_artifact(
    artifact_hash = "abcdefghi",
    version = "1.0.0",
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_artifact_hash_in_build_pom_released_content(content, "abcdefghi"))

    def test_update_released_version(self):
        content = """
released_maven_artifact(
    artifact_hash = "123456789",
    version = "1.0.0",
)
"""
        expected_content = """
released_maven_artifact(
    artifact_hash = "123456789",
    version = "2.0.0",
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_in_build_pom_released_content(content, "2.0.0"))

    def test_update_version__double_quotes(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)
"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "2.0.0",
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_in_build_pom_content(content, "2.0.0"))

    def test_update_version__single_quotes(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = '1.0.0',
)
"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = '2.0.0',
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_in_build_pom_content(content, "2.0.0"))

    def test_update_version__spaces(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version=   "1.0.0   ",
)
"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version=   "2.0.0",
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_in_build_pom_content(content, "2.0.0"))

    def test_update_version__no_trailing_comma(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version="1.0.0"
)
"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version="2.0.0"
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_in_build_pom_content(content, "2.0.0"))

    def test_update_version_increment_strategy__double_quotes(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = "patch",
)

"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = "minor",
)

"""
        self.assertEqual(expected_content, buildpomupdate._update_version_incr_strategy_in_build_pom_content(content, "minor"))

    def test_update_version_increment_strategy__single_quotes(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = 'major',
)

"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = 'patch',
)

"""
        self.assertEqual(expected_content, buildpomupdate._update_version_incr_strategy_in_build_pom_content(content, "patch"))

    def test_update_version_increment_strategy__no_trailing_comma(self):
        content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = 'patch'
)

"""
        expected_content = """
maven_artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "1.0.0",
)

maven_artifact_update(
    version_increment_strategy = 'minor'
)

"""
        self.assertEqual(expected_content, buildpomupdate._update_version_incr_strategy_in_build_pom_content(content, "minor"))

    def test_add_missing_version_increment_strategy(self):
        content = """
maven_artifact(
    group_id = "g1",
    artifact_id = "a1",
    version = "1.2.3",
)
"""
        expected_content = """
maven_artifact(
    group_id = "g1",
    artifact_id = "a1",
    version = "1.2.3",
)

maven_artifact_update(
    version_increment_strategy = "patch",
)
"""
        self.assertEqual(expected_content, buildpomupdate._update_version_incr_strategy_in_build_pom_content(content, "patch"))

    def test_update_version_in_BUILD_pom(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3")

        buildpomupdate.update_build_pom_file(repo_root, [package_rel_path],
                                             "4.5.6")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "4.5.6"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__use_version_strategy(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")

        buildpomupdate.update_build_pom_file(
            repo_root, [package_rel_path], new_version=None,
            update_version_using_version_incr_strat=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "2.0.0"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")
        self._write_build_pom_released(repo_package, "10.9.8", "abcdef")

        buildpomupdate.update_build_pom_file(
            repo_root, [package_rel_path], new_version=None,
            set_version_to_last_released_version=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "10.9.8"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version__multiple_files(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "1.1.1-SNAPSHOT",
                              version_increment_strategy="major")
        self._write_build_pom_released(pack1_path, "9.9.9", "abcdef")

        pack2_path = os.path.join(repo_root, pack2)
        os.makedirs(pack2_path)
        self._write_build_pom(pack2_path, "p2a", "p2g", "2.2.2",
                              version_increment_strategy="major")
        self._write_build_pom_released(pack2_path, "10.10.10", "abcdef")

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1, pack2], new_version=None,
            set_version_to_last_released_version=True)

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "9.9.9"', content)
            self.assertIn(')', content)

        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p2g"', content)
            self.assertIn('artifact_id = "p2a"', content)
            self.assertIn('version = "10.10.10"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version__no_build_pom_released_file(self):
        package_rel_path = "package1/package2"
        repo_root = tempfile.mkdtemp("monorepo")
        repo_package = os.path.join(repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")

        buildpomupdate.update_build_pom_file(
            repo_root, [package_rel_path], new_version=None,
            set_version_to_last_released_version=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "1.1.1-SNAPSHOT",
                              version_increment_strategy="major")

        pack2_path = os.path.join(repo_root, pack2)
        os.makedirs(pack2_path)
        self._write_build_pom(pack2_path, "p2a", "p2g", "2.2.2",
                              version_increment_strategy="major")

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1, pack2], version_qualifier_to_add="the_qual")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "1.1.1-the_qual-SNAPSHOT"', content)
            self.assertIn(')', content)

        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p2g"', content)
            self.assertIn('artifact_id = "p2a"', content)
            self.assertIn('version = "2.2.2-the_qual"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__slashes_are_removed(self):
        pack1 = "somedir/p1"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              version_increment_strategy="major")

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1], version_qualifier_to_add="-the_qual-")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-the_qual"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__non_snapshot_qualifiers_are_appended(self):
        pack1 = "somedir/p1"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              version_increment_strategy="major")

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1], version_qualifier_to_add="rel1")
        buildpomupdate.update_build_pom_file(
            repo_root, [pack1], version_qualifier_to_add="rel2")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-rel1-rel2"', content)
            self.assertIn(')', content)

    def test_update_pom_generation_mode_in_BUILD_pom(self):
        pack1 = "somedir/p1"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              pom_generation_mode="jar")

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1], new_pom_generation_mode="template")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('maven_artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1"', content)
            self.assertIn('pom_generation_mode = "template"', content)
            self.assertIn(')', content)

    def test_add_pom_generation_mode_to_BUILD_pom(self):
        pack1 = "somedir/p1"
        repo_root = tempfile.mkdtemp("monorepo")
        pack1_path = os.path.join(repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              pom_generation_mode=None)

        buildpomupdate.update_build_pom_file(
            repo_root, [pack1], new_pom_generation_mode="mypomgenmode")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            print(content)
            self.assertIn('maven_artifact(', content)
            self.assertIn('    group_id = "p1g"', content)
            self.assertIn('    artifact_id = "p1a"', content)
            self.assertIn('    version = "3.2.1"', content)
            self.assertIn('    pom_generation_mode = "mypomgenmode"', content)
            self.assertIn(')', content)

    def _write_build_pom(self, package_path, artifact_id, group_id, version,
                         pom_generation_mode=None,
                         version_increment_strategy="minor"):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s","""

        build_pom = build_pom % (artifact_id, group_id, version)

        if pom_generation_mode is not None:
            build_pom += "    pom_generation_mode = \"%s\"," % pom_generation_mode

        build_pom += """
)

maven_artifact_update(
    version_increment_strategy = "%s",
)
"""
        build_pom = build_pom % version_increment_strategy

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

    def _setup_repo(self, repo_root_path):
        run_cmd("git init .", cwd=repo_root_path)
        run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        self._commit(repo_root_path)

    def _commit(self, repo_root_path):
        run_cmd("git add .", cwd=repo_root_path)
        run_cmd("git commit --allow-empty --no-gpg-sign -m 'test commit'", cwd=repo_root_path)

    def _touch_file_at_path(self, repo_root_path, package_rel_path, filename):
        path = os.path.join(repo_root_path, package_rel_path, filename)
        if os.path.exists(path):
            with open(path, "r+") as f:
                content = f.read()
                content += "abc\n"
                f.seek(0)
                f.write(content)
                f.truncate()
        else:
            with open(path, "w") as f:
                f.write("abc\n")

if __name__ == '__main__':
    unittest.main()

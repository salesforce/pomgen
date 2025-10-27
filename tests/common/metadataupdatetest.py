"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import common.metadataupdate as metadataupdate
import common.os_util as os_util
import config.config as config
import config.exclusions as exclusions
import crawl.git as git
import crawl.workspace as workspace
import common.manifestcontent as manifestcontent
import generate.generationstrategyfactory as generationstrategyfactory
import os
import tempfile
import unittest


class MetadataUpdateTest(unittest.TestCase):

    def setUp(self):
        self.repo_root = tempfile.mkdtemp("repo")
        cfg = config.Config()
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root, cfg, manifestcontent.NOOP, verbose=True)
        self.workspace = workspace.Workspace(self.repo_root, cfg, self.fac, cache_artifact_defs=False)        

    def test_update_BUILD_pom_released__set_artifact_hash_to_current(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(os.path.join(pack1_path))
        pack2_path = os.path.join(self.repo_root, pack2)
        os.makedirs(os.path.join(pack2_path))
        self._write_build_pom(pack1_path, "a1", "g1", "1.2.3", "dynamic")
        self._write_build_pom_released(pack1_path, "1.0.0", "aaa")
        self._write_build_pom(pack2_path, "a1", "g1", "1.2.3", "dynamic")
        self._write_build_pom_released(pack2_path, "1.0.0", "bbb")
        self._setup_repo(self.repo_root)
        self._commit(self.repo_root)
        self._touch_file_at_path(self.repo_root, pack1, "blah1")
        self._commit(self.repo_root)
        pack1_hash = git.get_dir_hash(self.repo_root, [pack1], exclusions.src_exclusions(),
                                      git_repo_must_exist=True)
        self._touch_file_at_path(self.repo_root, pack2, "blah2")
        self._commit(self.repo_root)
        pack2_hash = git.get_dir_hash(self.repo_root, [pack2], exclusions.src_exclusions(),
                                      git_repo_must_exist=True)
        self.assertNotEqual(pack1_hash, pack2_hash)

        metadataupdate.update_released_artifact(
            self.repo_root, [pack1, pack2], self.fac,
            exclusions.src_exclusions(), use_current_artifact_hash=True)

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack1_hash, content)
        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack2_hash, content)

    def test_update_BUILD_pom_released__set_artifact_hash_to_current__with_change_detected_packages(self):
        pack1 = "somedirs/p1"
        pack2 = "somedirs/p2"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(os.path.join(pack1_path))
        pack2_path = os.path.join(self.repo_root, pack2)
        os.makedirs(os.path.join(pack2_path))
        self._write_build_pom(pack1_path, "p1", "g1", "0.0.0",
                              generation_mode="dynamic")
        self._write_build_pom_released(pack1_path, "1.0.0", "aaa")
        self._write_build_pom(pack2_path, "p2", "g2", "0.0.0",
                              generation_mode="dynamic",
                              additional_change_detected_packages=[pack1])
        self._write_build_pom_released(pack2_path, "1.0.0", "bbb")
        self._setup_repo(self.repo_root)
        self._commit(self.repo_root)
        self._touch_file_at_path(self.repo_root, pack1, "blah1")
        self._commit(self.repo_root)
        pack1_hash = git.get_dir_hash(self.repo_root, [pack1], exclusions.src_exclusions(),
                                      git_repo_must_exist=True)
        self._touch_file_at_path(self.repo_root, pack2, "blah2")
        self._commit(self.repo_root)
        pack2_hash = git.get_dir_hash(self.repo_root, [pack2, pack1], exclusions.src_exclusions(),
                                      git_repo_must_exist=True)
        self.assertNotEqual(pack1_hash, pack2_hash)

        metadataupdate.update_released_artifact(
            self.repo_root, [pack1, pack2], self.fac,
            exclusions.src_exclusions(), use_current_artifact_hash=True)

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack1_hash, content)
        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('artifact_hash = "%s"' % pack2_hash, content)

    def test_update_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "p1", "g1", "0.0.0",
                              generation_mode="dynamic")
        self._write_build_pom_released(repo_package, "1.0.0", "aaa")
        # sanity:
        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('version = "1.0.0"', content)
            self.assertIn('artifact_hash = "aaa"', content)

        metadataupdate.update_released_artifact(
            self.repo_root, [package_rel_path], self.fac,
            exclusions.src_exclusions(), "1.2.3", "abc")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('released_artifact(', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn('artifact_hash = "abc"', content)

    def test_create_BUILD_pom_released(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "p1", "g1", "0.0.0",
                              generation_mode="dynamic")

        metadataupdate.update_released_artifact(
            self.repo_root, [package_rel_path], self.fac,
            exclusions.src_exclusions(), "1.2.3", "abc")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom.released"), "r") as f:
            content = f.read()
            self.assertIn('released_artifact(', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn('artifact_hash = "abc"', content)

    def test_get_build_pom_released_content(self):
        expected_content = """released_artifact(
    version = "1.0.0",
    artifact_hash = "abcdefghi",
)
"""
        self.assertEqual(expected_content, metadataupdate._get_released_metadata("1.0.0", "abcdefghi"))

    def test_update_released_artifact_hash(self):
        content = """
released_artifact(
    artifact_hash = "123456789",
    version = "1.0.0",
)
"""
        expected_content = """
released_artifact(
    artifact_hash = "abcdefghi",
    version = "1.0.0",
)
"""
        self.assertEqual(expected_content, metadataupdate._update_artifact_hash_in_released_metadata(content, "abcdefghi"))
    def test_update_released_version(self):
        content = """
released_artifact(
    artifact_hash = "123456789",
    version = "1.0.0",
)
"""
        expected_content = """
released_artifact(
    artifact_hash = "123456789",
    version = "2.0.0",
)
"""
        self.assertEqual(expected_content, metadataupdate._update_version_in_released_metadata(content, "2.0.0"))

    def test_update_version_in_BUILD_pom(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3")

        metadataupdate.update_artifact(
            self.repo_root, [package_rel_path], self.workspace,
            new_version="4.5.6")

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            self.assertEqual(f.read(), """
artifact(
    artifact_id = "a1",
    group_id = "g1",
    version = "4.5.6",
    generation_mode = "dynamic",

)

artifact_update(
    version_increment_strategy = "minor",
)
""")

    def test_update_version_in_BUILD_pom__use_version_increment_strategy(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [package_rel_path], self.workspace,
            update_version_using_incr_strat=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "2.0.0"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__use_version_increment_strategy__snap(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3-SNAPSHOT",
                              version_increment_strategy="patch")

        metadataupdate.update_artifact(
            self.repo_root, [package_rel_path], self.workspace,
            update_version_using_incr_strat=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "1.2.4-SNAPSHOT"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")
        self._write_build_pom_released(repo_package, "10.9.8", "abcdef")

        metadataupdate.update_artifact(
            self.repo_root, [package_rel_path], self.workspace,
            set_version_to_last_released_version=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "10.9.8"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version__multiple_files(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "1.1.1-SNAPSHOT",
                              version_increment_strategy="major")
        self._write_build_pom_released(pack1_path, "9.9.9", "abcdef")

        pack2_path = os.path.join(self.repo_root, pack2)
        os.makedirs(pack2_path)
        self._write_build_pom(pack2_path, "p2a", "p2g", "2.2.2",
                              version_increment_strategy="major")
        self._write_build_pom_released(pack2_path, "10.10.10", "abcdef")

        metadataupdate.update_artifact(
            self.repo_root, [pack1, pack2], self.workspace,
            set_version_to_last_released_version=True)

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "9.9.9"', content)
            self.assertIn(')', content)

        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p2g"', content)
            self.assertIn('artifact_id = "p2a"', content)
            self.assertIn('version = "10.10.10"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__set_to_last_released_version__no_build_pom_released_file(self):
        package_rel_path = "package1/package2"
        repo_package = os.path.join(self.repo_root, package_rel_path)
        os.makedirs(repo_package)
        self._write_build_pom(repo_package, "a1", "g1", "1.2.3",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [package_rel_path], self.workspace,
            set_version_to_last_released_version=True)

        with open(os.path.join(repo_package, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "g1"', content)
            self.assertIn('artifact_id = "a1"', content)
            self.assertIn('version = "1.2.3"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier(self):
        pack1 = "somedir/p1"
        pack2 = "somedir/p2"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "1.1.1-SNAPSHOT",
                              version_increment_strategy="major")

        pack2_path = os.path.join(self.repo_root, pack2)
        os.makedirs(pack2_path)
        self._write_build_pom(pack2_path, "p2a", "p2g", "2.2.2",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1, pack2], self.workspace,
            version_qualifier_to_add="the_qual")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "1.1.1-the_qual-SNAPSHOT"', content)
            self.assertIn(')', content)

        with open(os.path.join(pack2_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p2g"', content)
            self.assertIn('artifact_id = "p2a"', content)
            self.assertIn('version = "2.2.2-the_qual"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__rm_version_qualifier__with_dash(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-foo-blah",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_remove="-foo")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-blah"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__rm_version_qualifier__without_dash(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-SNAPSHOT",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_remove="SNAPSHOT")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__rm_version_qualifier__substr1(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-SNAPSHOT",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_remove="SNAP")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__rm_version_qualifier__substr2(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-foo-blah",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace, version_qualifier_to_remove="fo")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-blah"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__rm_version_qualifier__substr3(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-foo-rel9",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_remove="rel")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-foo"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__slashes_are_removed(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_add="-the_qual-")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-the_qual"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__non_snapshot_qualifiers_are_appended(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace, version_qualifier_to_add="rel1")
        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace, version_qualifier_to_add="rel2")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            self.assertIn('version = "3.2.1-rel1-rel2"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__duplicate_is_not_repeated(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-casino",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_add="casino")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            # -casino is not appended if the version ends with -casino already
            self.assertIn('version = "3.2.1-casino"', content)
            self.assertIn(')', content)

    def test_update_version_in_BUILD_pom__add_version_qualifier__no_duplicate_SNAPSHOT(self):
        pack1 = "somedir/p1"
        pack1_path = os.path.join(self.repo_root, pack1)
        os.makedirs(pack1_path)
        self._write_build_pom(pack1_path, "p1a", "p1g", "3.2.1-SNAPSHOT",
                              version_increment_strategy="major")

        metadataupdate.update_artifact(
            self.repo_root, [pack1], self.workspace,
            version_qualifier_to_add="SNAPSHOT")

        with open(os.path.join(pack1_path, "MVN-INF", "BUILD.pom"), "r") as f:
            content = f.read()
            self.assertIn('artifact(', content)
            self.assertIn('group_id = "p1g"', content)
            self.assertIn('artifact_id = "p1a"', content)
            # -SNAPSHOT is not added if the version ends with -SNAPSHOT already
            self.assertIn('version = "3.2.1-SNAPSHOT"', content)
            self.assertIn(')', content)

    def _write_build_pom(self, package_path, artifact_id, group_id, version,
                         generation_mode="dynamic",
                         version_increment_strategy="minor",
                         additional_change_detected_packages=None):
        build_pom = """
artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
"""

        build_pom = build_pom % (artifact_id, group_id, version)

        if generation_mode is not None:
            build_pom += "    generation_mode = \"%s\",\n" % generation_mode

        if additional_change_detected_packages is not None:
              build_pom += "    additional_change_detected_packages = [%s]," % ",".join(["'%s'" % p for p in additional_change_detected_packages])

        build_pom += """
)

artifact_update(
    version_increment_strategy = "%s",
)
"""
        build_pom = build_pom % version_increment_strategy

        path = os.path.join(package_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
           f.write(build_pom)

        # parsing requires a LIBRARY.root file so we are adding it here
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
           f.write("")

    def _write_build_pom_released(self, package_path, released_version, released_artifact_hash):
        build_pom_released = """
released_artifact(
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
        os_util.run_cmd("git init .", cwd=repo_root_path)
        os_util.run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        os_util.run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        self._commit(repo_root_path)

    def _commit(self, repo_root_path):
        os_util.run_cmd("git add .", cwd=repo_root_path)
        os_util.run_cmd("git commit --allow-empty --no-gpg-sign -m 'test commit'", cwd=repo_root_path)

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

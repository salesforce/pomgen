"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import artifactprocessor
from crawl import buildpom
from crawl import git
from crawl import releasereason
from common.os_util import run_cmd
from config import exclusions
import os
import tempfile
import unittest

class ArtifactProcessorTest(unittest.TestCase):

    def test_artifact_def_without_relased_artifact_hash(self):        
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0", bazel_package="")
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root, "", "MVN-INF", "LIBRARY.root")
        self.assertIs(None, art_def.released_artifact_hash)

        art_def = artifactprocessor.augment_artifact_def(repo_root, art_def, exclusions.src_exclusions())

        self.assertTrue(art_def.requires_release)

    def test_library_root(self):
        repo_root = tempfile.mkdtemp("monorepo")
        art_def_1 = buildpom.MavenArtifactDef("g1", "a1", "1.0.0", bazel_package="lib1/pack1")
        self._touch_file_at_path(repo_root, "lib1", "MVN-INF", "LIBRARY.root")
        art_def_2 = buildpom.MavenArtifactDef("g1", "a2", "1.0.0", bazel_package="foo/lib2/pack1")
        self._touch_file_at_path(repo_root, "foo/lib2", "MVN-INF", "LIBRARY.root")

        art_def_1 = artifactprocessor.augment_artifact_def(repo_root, art_def_1, exclusions.src_exclusions())
        art_def_2 = artifactprocessor.augment_artifact_def(repo_root, art_def_2, exclusions.src_exclusions())

        self.assertEqual("lib1", art_def_1.library_path)
        self.assertEqual("foo/lib2", art_def_2.library_path)

    def test_library_root_in_package_dir(self):
        repo_root = tempfile.mkdtemp("monorepo")
        art_def_1 = buildpom.MavenArtifactDef("g1", "a1", "1.0.0", bazel_package="lib1/pack1")
        self._touch_file_at_path(repo_root, "lib1/pack1", "MVN-INF", "LIBRARY.root")

        art_def_1 = artifactprocessor.augment_artifact_def(repo_root, art_def_1, exclusions.src_exclusions())

        self.assertEqual("lib1/pack1", art_def_1.library_path)

    def test_missing_library_root_file(self):
        repo_root = tempfile.mkdtemp("monorepo")
        art_def_1 = buildpom.MavenArtifactDef("g1", "a1", "1.0.0", bazel_package="lib1/pack1")

        with self.assertRaises(Exception) as ctx:
            artifactprocessor.augment_artifact_def(repo_root, art_def_1, exclusions.src_exclusions())

        self.assertIn("Did not find LIBRARY.root at", str(ctx.exception))
        self.assertIn("or any parent dir", str(ctx.exception))

    def test_artifact_without_changes_since_last_release(self):
        repo_root_path = self._setup_repo_with_package("pack1/pack2")
        current_artifact_hash = git.get_dir_hash(repo_root_path, "pack1/pack2", exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package="pack1/pack2", released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)
        self.assertEqual(None, art_def.release_reason)

    def test_artifact_without_changes_always_release(self):
        repo_root_path = self._setup_repo_with_package("pack1/pack2")
        current_artifact_hash = git.get_dir_hash(repo_root_path, "pack1/pack2", exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package="pack1/pack2", released_version="1.2.0", released_artifact_hash=current_artifact_hash, change_detection=False)

        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertTrue(art_def.requires_release, "Expected artifact to require release")
        self.assertEqual(releasereason.ReleaseReason.ALWAYS, art_def.release_reason)

    def test_artifact_with_changes_since_last_release__new_file(self):
        package = "pack1/pack2"
        repo_root_path = self._setup_repo_with_package(package)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", released_version="1.2.0", bazel_package=package, released_artifact_hash=current_artifact_hash)
        # add a new file:
        self._touch_file_at_path(repo_root_path, package, "", "Foo.java")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertTrue(art_def.requires_release, "Expected artifact to require release")
        self.assertIs(releasereason.ReleaseReason.ARTIFACT, art_def.release_reason)

    def test_artifact_with_changes_since_last_release__modified_file(self):
        package = "pack1/pack2"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "", "Blah.java")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", released_version="1.2.0", bazel_package=package, released_artifact_hash=current_artifact_hash)
        # modify an existing file:
        self._touch_file_at_path(repo_root_path, package, "", "Blah.java")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertTrue(art_def.requires_release, "Expected artifact to require release")
        self.assertIs(releasereason.ReleaseReason.ARTIFACT, art_def.release_reason)

    def test_build_pom_changes_are_ignored(self):
        package = "a/b/c"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom")
        self._touch_file_at_path(repo_root_path, package, "", "some_file")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update BUILD.pom and commit - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)

    def test_dot_md_changes_are_ignored(self):
        src_exclusions = exclusions.src_exclusions(file_extensions=(".md",))
        package = "a/b/c"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom")
        self._touch_file_at_path(repo_root_path, package, "docs", "f.md")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, src_exclusions)
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update .md file - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "docs", "f.md")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, src_exclusions)

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)

    def test_dot_gitignore_changes_are_ignored(self):
        src_exclusions = exclusions.src_exclusions(file_names=(".gitignore",))
        package = "a/b/c"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom")
        self._touch_file_at_path(repo_root_path, package, "f", ".gitignore")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, src_exclusions)
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update .md file - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "f", ".gitignore")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, src_exclusions)

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)
        
    def test_build_pom_released_changes_are_ignored(self):
        package = "a/b/c"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom.released")
        self._touch_file_at_path(repo_root_path, package, "", "some_file")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update BUILD.pom.released and commit - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom.released")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)

    def test_pom_released_changes_are_ignored(self):
        package = "a/b/c"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "pom.xml.released")
        self._touch_file_at_path(repo_root_path, package, "", "some_file")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, exclusions.src_exclusions())
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update pom.xml.released and commit - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "pom.xml.released")
        self._commit(repo_root_path)
        
        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, exclusions.src_exclusions())

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)

    def test_test_changes_are_ignored(self):
        """
        We are assuming the de-facto Maven directory structure standard:
            src/main/... - prod code
            src/test/... - tests
        """
        src_exclusions = exclusions.src_exclusions(relative_paths=("src/test",))
        package = "pack"
        repo_root_path = self._setup_repo_with_package(package)
        self._touch_file_at_path(repo_root_path, package, "MVN-INF", "BUILD.pom.released")
        self._touch_file_at_path(repo_root_path, package, "src/main", "MyClass.java")
        self._touch_file_at_path(repo_root_path, package, "src/test", "MyTest.java")
        self._commit(repo_root_path)
        current_artifact_hash = git.get_dir_hash(repo_root_path, package, src_exclusions)
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.1.0", bazel_package=package, released_version="1.2.0", released_artifact_hash=current_artifact_hash)
        # update test class and commit - that change should be ignored
        self._touch_file_at_path(repo_root_path, package, "src/test", "MyTest.java")
        self._commit(repo_root_path)

        art_def = artifactprocessor.augment_artifact_def(repo_root_path, art_def, src_exclusions)

        self.assertNotEqual(None, art_def.requires_release)
        self.assertFalse(art_def.requires_release)

    def test_nested_metadata_file_changes_are_ignored(self):
        """
        lib/a1/src/...
        lib/a1/MVN-INF/...
        lib/a1/a2/src/...
        lib/a1/a2/MVN-INF/...

        Changes to files in lib/a1/a2/MVN-INF should be ignored by
        lib/a1's hash calculation.
        """
        a1_package = "lib/a1"
        a2_package = "lib/a1/a2"
        repo_root_path = self._setup_repo_with_package(a1_package)
        self._touch_file_at_path(repo_root_path, a1_package, "MVN-INF", "BUILD.pom.released")
        self._touch_file_at_path(repo_root_path, a1_package, "", "some_file")

        self._touch_file_at_path(repo_root_path, a2_package, "MVN-INF", "BUILD.pom.released")
        self._touch_file_at_path(repo_root_path, a2_package, "", "some_file")

        self._commit(repo_root_path)

        a1_hash = git.get_dir_hash(repo_root_path, a1_package, exclusions.src_exclusions())
        # modify file under a2 metadata - should be ignored
        self._touch_file_at_path(repo_root_path, a2_package, "MVN-INF", "BUILD.pom.released")
        self._commit(repo_root_path)

        updated_a1_hash = git.get_dir_hash(repo_root_path, a1_package, exclusions.src_exclusions())

        self.assertEqual(a1_hash, updated_a1_hash)

    def _setup_repo_with_package(self, package_rel_path):
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(repo_root_path, "", "MVN-INF", "LIBRARY.root")
        repo_package = os.path.join(repo_root_path, package_rel_path)
        os.makedirs(repo_package)
        self._touch_file_at_path(repo_root_path, package_rel_path, "MVN-INF", "BUILD")
        run_cmd("git init .", cwd=repo_root_path)
        run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        run_cmd("git config commit.gpgsign false", cwd=repo_root_path)
        run_cmd("git add .", cwd=repo_root_path)
        run_cmd("git commit -m 'test commit'", cwd=repo_root_path)
        return repo_root_path

    def _touch_file_at_path(self, repo_root_path, package_rel_path, within_package_rel_path, file_path):
        abs_path = os.path.join(repo_root_path, package_rel_path, within_package_rel_path, file_path)
        dir_path = os.path.dirname(abs_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if os.path.exists(abs_path):
            with open(abs_path, "r+") as f:
                content = f.read()
                content += "abc\n"
                f.seek(0)
                f.write(content)
                f.truncate()
        else:
            with open(abs_path, "w") as f:
                f.write("abc\n")

    def _commit(self, repo_root_path):
        run_cmd("git add .", repo_root_path)
        run_cmd("git commit -m 'message'", repo_root_path)

if __name__ == '__main__':
    unittest.main()

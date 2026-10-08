"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import os
import tempfile
import unittest
from unittest.mock import patch
from common import version_increment_strategy as vis
from crawl.buildpom import MavenArtifactDef
from packagemanager import nexus


class GetNextAvailableVersionTest(unittest.TestCase):

    def test_version_available_on_first_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', return_value=False):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", "http://nexus", strat)

        self.assertEqual("1.0.0", result)


    def test_version_available_on_third_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', side_effect=[True, True, False]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", "http://nexus", strat)

        self.assertEqual("1.2.0", result)


    def test_rel_qualifier_version_available_on_first_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_rel_qualifier_increment_strategy("1.0.0-rel1", "1.0.0")

        with patch.object(nexus, '_head_requests', return_value=False):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0-rel1", "http://nexus", strat)

        self.assertEqual("1.0.0-rel1", result)

    def test_rel_qualifier_version_available_on_third_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_rel_qualifier_increment_strategy("1.0.0-rel1", "1.0.0")

        with patch.object(nexus, '_head_requests', side_effect=[True, True, False]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0-rel1", "http://nexus", strat)

        self.assertEqual("1.0.0-rel3", result)


class GetNextAvailableVersionFileUrlTest(unittest.TestCase):

    def _touch_pom(self, repo_root, art_def, version):
        group_path = art_def.group_id.replace(".", "/")
        pom_dir = os.path.join(repo_root, group_path, art_def.artifact_id, version)
        os.makedirs(pom_dir)
        pom_path = os.path.join(pom_dir, "%s-%s.pom" % (art_def.artifact_id, version))
        open(pom_path, "w").close()

    def test_version_available_on_first_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with tempfile.TemporaryDirectory() as repo_root:
            nexus_artifact_url = "file://%s" % repo_root
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", nexus_artifact_url, strat)

        self.assertEqual("1.0.0", result)

    def test_version_available_on_third_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with tempfile.TemporaryDirectory() as repo_root:
            self._touch_pom(repo_root, artifacts[0], "1.0.0")
            self._touch_pom(repo_root, artifacts[0], "1.1.0")
            nexus_artifact_url = "file://%s" % repo_root
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", nexus_artifact_url, strat)

        self.assertEqual("1.2.0", result)

    def test_tilde_in_url_is_expanded_to_home_dir(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with tempfile.TemporaryDirectory() as fake_home:
            self._touch_pom(fake_home, artifacts[0], "1.0.0")
            with patch.dict(os.environ, {"HOME": fake_home}):
                result = nexus.get_next_available_version(
                    artifacts, "1.0.0", "file://~", strat)

        self.assertEqual("1.1.0", result)


if __name__ == "__main__":
    unittest.main()

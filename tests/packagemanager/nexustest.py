"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import functools
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

        with patch.object(nexus, '_head_requests', return_value=["404"]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", "http://nexus", strat)

        self.assertEqual("1.0.0", result)


    def test_version_available_on_third_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', side_effect=[["200"], ["200"], ["404"]]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0", "http://nexus", strat)

        self.assertEqual("1.2.0", result)


    def test_rel_qualifier_version_available_on_first_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_rel_qualifier_increment_strategy("1.0.0-rel1", "1.0.0")

        with patch.object(nexus, '_head_requests', return_value=["404"]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0-rel1", "http://nexus", strat)

        self.assertEqual("1.0.0-rel1", result)

    def test_rel_qualifier_version_available_on_third_try(self):
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_rel_qualifier_increment_strategy("1.0.0-rel1", "1.0.0")

        with patch.object(nexus, '_head_requests', side_effect=[["200"], ["200"], ["404"]]):
            result = nexus.get_next_available_version(
                artifacts, "1.0.0-rel1", "http://nexus", strat)

        self.assertEqual("1.0.0-rel3", result)


if __name__ == "__main__":
    unittest.main()

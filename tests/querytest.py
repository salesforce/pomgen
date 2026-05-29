"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from unittest.mock import patch
from common import version_increment_strategy as vis
from crawl.buildpom import MavenArtifactDef
from crawl.libaggregator import LibraryNode
from packagemanager import nexus
import query


class ComputeProposedNextVersionsTest(unittest.TestCase):

    def test_no_nexus_check(self):
        node = LibraryNode(
            library_path="libs/foo",
            requires_release=True,
            release_reason="something changed",
            version="1.0.0",
            md_version="1.0.0-SNAPSHOT",
            released_version="0.9.0",
            version_increment_strategy_name="minor")
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', return_value=["404"]):
            rel_vers, dev_vers = query._compute_proposed_next_versions(
                node, [], strat, None)

        self.assertEqual("1.0.0", rel_vers)
        self.assertEqual("1.1.0-SNAPSHOT", dev_vers)


    def test_compute_proposed_next_versions__version_available_on_first_try(self):
        node = LibraryNode(
            library_path="libs/foo",
            requires_release=True,
            release_reason="something changed",
            version="1.0.0",
            md_version="1.0.0-SNAPSHOT",
            released_version="0.9.0",
            version_increment_strategy_name="minor")
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', return_value=["404"]):
            rel_vers, dev_vers = query._compute_proposed_next_versions(
                node, artifacts, strat, "http://nexus")

        self.assertEqual("1.0.0", rel_vers)
        self.assertEqual("1.1.0-SNAPSHOT", dev_vers)

    def test_compute_proposed_next_versions__version_available_on_third_try(self):
        node = LibraryNode(
            library_path="libs/foo",
            requires_release=True,
            release_reason="something changed",
            version="1.0.0",
            md_version="1.0.0-SNAPSHOT",
            released_version="0.9.0",
            version_increment_strategy_name="minor")
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_version_increment_strategy_by_name("minor")

        with patch.object(nexus, '_head_requests', side_effect=[["200"], ["200"], ["404"]]):
            rel_vers, dev_vers = query._compute_proposed_next_versions(
                node, artifacts, strat, "http://nexus")

        self.assertEqual("1.2.0", rel_vers)
        self.assertEqual("1.3.0-SNAPSHOT", dev_vers)

    def test_compute_proposed_next_versions__rel_qualifier__version_available_on_second_try(self):
        node = LibraryNode(
            library_path="libs/foo",
            requires_release=True,
            release_reason="something changed",
            version="1.0.0",
            md_version="1.0.0-SNAPSHOT",
            released_version="1.0.0-rel1",
            version_increment_strategy_name="minor")
        artifacts = [
            MavenArtifactDef(group_id="com.example", artifact_id="foo",
                             version="1.0.0", library_path="libs/foo"),
        ]
        strat = vis.get_rel_qualifier_increment_strategy("1.0.0-SNAPSHOT", "1.0.0-rel1")

        with patch.object(nexus, '_head_requests', side_effect=[["200"], ["404"]]):
            rel_vers, dev_vers = query._compute_proposed_next_versions(
                node, artifacts, strat, "http://nexus")

        self.assertEqual("1.0.0-rel3", rel_vers)
        self.assertEqual("1.0.0-SNAPSHOT", dev_vers)


if __name__ == "__main__":
    unittest.main()

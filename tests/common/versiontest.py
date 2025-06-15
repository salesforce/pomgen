"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from common import version


class VersionTest(unittest.TestCase):

    def test_parse_build_pom_version(self):
        build_pom = """
maven_artifact(
    group_id = "g1",
    artifact_id = "a1",
    version = "1.2.3",
)
maven_artifact_update(
    version_increment_strategy = "major",
)
"""
        self.assertEqual("1.2.3", version.parse_build_pom_version(build_pom))

    def test_parse_build_pom_released_version(self):
        content = """
released_maven_artifact(
    artifact_hash = "123456789",
    version = "1.2.3",
)
"""
        self.assertEqual("1.2.3", version.parse_build_pom_released_version(content))

    def _get_build_pom(self, version_increment_strategy):
        build_pom = """
maven_artifact(
    artifact_id = "art",
    group_id = "group",
    version = 1
)
maven_artifact_update(
    version_increment_strategy = "%s",
)
"""
        return build_pom % version_increment_strategy


if __name__ == '__main__':
    unittest.main()

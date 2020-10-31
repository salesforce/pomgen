"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from common import version

class VersionTest(unittest.TestCase):

    def test_get_release_version__semver_release(self):
        self.assertEqual("1.2.3", version.get_release_version("1.2.3-SNAPSHOT"))
        self.assertEqual("1.2.3", version.get_release_version("1.2.3"))

    def test_get_release_version__incremental_release(self):
        self.assertEqual("1.2.3-rel-1", version.get_release_version("foo", last_released_version="1.2.3", incremental_release=True))
        self.assertEqual("1.2.3-rel-2", version.get_release_version("foo", last_released_version="1.2.3-rel-1", incremental_release=True))
        self.assertEqual("0.0.0-rel-1", version.get_release_version("foo", last_released_version=None, incremental_release=True))

    def test_get_next_dev_version__semver_release(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        
        self.assertEqual("2.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0", s))

    def test_get_next_dev_version__semver_release__snap(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        
        self.assertEqual("2.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0-SNAPSHOT", s))

    def test_get_next_dev_version__incremental_release(self):
        build_pom_content = self._get_build_pom("major")
        not_used = version.get_version_increment_strategy(build_pom_content, None)

        self.assertEqual("1.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0", not_used, incremental_release=True))

    def test_get_next_dev_version__incremental_release__snap(self):
        build_pom_content = self._get_build_pom("major")
        not_used = version.get_version_increment_strategy(build_pom_content, None)

        self.assertEqual("1.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0-SNAPSHOT", not_used, incremental_release=True))
 
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

    def test_get_next_version__major(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0", s("1.0.0"))

    def test_get_next_version__major__reset_minor(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0", s("1.2.0"))

    def test_get_next_version__major__reset_patch(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0", s("1.0.5"))

    def test_get_next_version__major_snap(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.0.0-SNAPSHOT"))

    def test_get_next_version__major_snap__reset_minor(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.2.0-SNAPSHOT"))

    def test_get_next_version__major_snap__reset_patch(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.2.5-SNAPSHOT"))

    def test_get_next_version__major_qual(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0-scone_60x", s("1.0.0-scone_60x"))

    def test_get_next_version__major_snap_and_qual(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.0.0-scone_60x-SNAPSHOT", s("1.0.0-scone_60x-SNAPSHOT"))

    def test_get_next_version__minor(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.0", s("1.0.0"))

    def test_get_next_version__minor__reset_patch(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.1.0", s("2.0.1"))

    def test_get_next_version__minor_snap(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.0-SNAPSHOT", s("1.0.0-SNAPSHOT"))

    def test_get_next_version__minor_qual(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.0-scone_60x", s("1.0.0-scone_60x"))

    def test_get_next_version__minor_snap_and_qual(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.0-scone_60x-SNAPSHOT", s("1.0.0-scone_60x-SNAPSHOT"))

    def test_get_next_version__minor_snap__reset_patch(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("2.1.0-SNAPSHOT", s("2.0.5-SNAPSHOT"))

    def test_get_next_version__patch(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("5.3.1", s("5.3.0"))

    def test_get_next_version__patch_snap(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.1-SNAPSHOT", s("1.1.0-SNAPSHOT"))

    def test_get_next_version__patch_qual(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.1-scone_70x", s("1.1.0-scone_70x"))

    def test_get_next_version__patch_snap_and_qual(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content, None)
        self.assertEqual("1.1.1-scone_70x-SNAPSHOT", s("1.1.0-scone_70x-SNAPSHOT"))

    def _get_build_pom(self, version_increment_strategy):
        build_pom = """
maven_artifact_update(
    version_increment_strategy = "%s",
)
"""
        return build_pom % version_increment_strategy

if __name__ == '__main__':
    unittest.main()

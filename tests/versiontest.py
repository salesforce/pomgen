"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from common import version
from datetime import datetime, timezone


class VersionTest(unittest.TestCase):

    def test_get_release_version__semver_release(self):
        self.assertEqual("1.2.3", version.get_release_version("1.2.3-SNAPSHOT"))
        self.assertEqual("1.2.3", version.get_release_version("1.2.3"))

    def test_get_release_version__incremental_release(self):
        self.assertEqual("1.2.3-rel1", version.get_release_version("foo", last_released_version="1.2.3", incremental_release=True))
        self.assertEqual("1.2.3-rel2", version.get_release_version("foo", last_released_version="1.2.3-rel1", incremental_release=True))
        self.assertEqual("0.0.0-rel1", version.get_release_version("foo", last_released_version=None, incremental_release=True))

    def test_get_release_version__incremental_release__multiple_digits(self):
        self.assertEqual("1.2.3-rel10", version.get_release_version("foo", last_released_version="1.2.3-rel9", incremental_release=True))
        self.assertEqual("1.2.3-rel11", version.get_release_version("foo", last_released_version="1.2.3-rel10", incremental_release=True))
        self.assertEqual("1.2.3-rel100", version.get_release_version("foo", last_released_version="1.2.3-rel99", incremental_release=True))

    def test_get_release_version__incremental_release__last_rel_qualifier_uses_old_dash_number_syntax(self):
        # we used to use rel-<num>, for example rel-1, rel-2 etc
        # we switched this to rel<num> (so rel1, rel2 etc) so that '-' is only
        # used as a separator between version qualifiers: 1.0.0-rel1-SNAPSHOT
        self.assertEqual("1.2.3-rel2", version.get_release_version("foo", last_released_version="1.2.3-rel-1", incremental_release=True))
        self.assertEqual("1.2.3-rel11", version.get_release_version("foo", last_released_version="1.2.3-rel-10", incremental_release=True))

    def test_get_release_version__multiple_qualifiers(self):
        self.assertEqual("1.2.3-rel2-foo22", version.get_release_version("foo", last_released_version="1.2.3-rel1-foo22", incremental_release=True))
        self.assertEqual("1.2.3-rel10-foo22", version.get_release_version("foo", last_released_version="1.2.3-rel9-foo22", incremental_release=True))
        self.assertEqual("1.2.3-rel2-foo22", version.get_release_version("foo", last_released_version="1.2.3-rel-1-foo22", incremental_release=True))
        self.assertEqual("1.2.3-rel10-foo22", version.get_release_version("foo", last_released_version="1.2.3-rel-9-foo22", incremental_release=True))

    def test_get_next_dev_version__semver_release(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        
        self.assertEqual("2.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0", s))

    def test_get_next_dev_version__semver_release__snap(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        
        self.assertEqual("2.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0-SNAPSHOT", s))

    def test_get_next_dev_version__incremental_release(self):
        build_pom_content = self._get_build_pom("major")
        not_used = version.get_version_increment_strategy(build_pom_content)

        self.assertEqual("1.0.0-SNAPSHOT", version.get_next_dev_version("1.0.0", not_used, incremental_release=True))

    def test_get_next_dev_version__incremental_release__snap(self):
        build_pom_content = self._get_build_pom("major")
        not_used = version.get_version_increment_strategy(build_pom_content)

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
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0", s("1.0.0"))

    def test_get_next_version__major__reset_minor(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0", s("1.2.0"))

    def test_get_next_version__major__reset_patch(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0", s("1.0.5"))

    def test_get_next_version__major_snap(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.0.0-SNAPSHOT"))

    def test_get_next_version__major_snap__reset_minor(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.2.0-SNAPSHOT"))

    def test_get_next_version__major_snap__reset_patch(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0-SNAPSHOT", s("1.2.5-SNAPSHOT"))

    def test_get_next_version__major_qual(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0-scone_60x", s("1.0.0-scone_60x"))

    def test_get_next_version__major_snap_and_qual(self):
        build_pom_content = self._get_build_pom("major")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.0.0-scone_60x-SNAPSHOT", s("1.0.0-scone_60x-SNAPSHOT"))

    def test_get_next_version__minor(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.0", s("1.0.0"))

    def test_get_next_version__minor__reset_patch(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.1.0", s("2.0.1"))

    def test_get_next_version__minor_snap(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.0-SNAPSHOT", s("1.0.0-SNAPSHOT"))

    def test_get_next_version__minor_qual(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.0-scone_60x", s("1.0.0-scone_60x"))

    def test_get_next_version__minor_snap_and_qual(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.0-scone_60x-SNAPSHOT", s("1.0.0-scone_60x-SNAPSHOT"))

    def test_get_next_version__minor_snap__reset_patch(self):
        build_pom_content = self._get_build_pom("minor")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("2.1.0-SNAPSHOT", s("2.0.5-SNAPSHOT"))

    def test_get_next_version__patch(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("5.3.1", s("5.3.0"))

    def test_get_next_version__patch_snap(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.1-SNAPSHOT", s("1.1.0-SNAPSHOT"))

    def test_get_next_version__patch_qual(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.1-scone_70x", s("1.1.0-scone_70x"))

    def test_get_next_version__patch_snap_and_qual(self):
        build_pom_content = self._get_build_pom("patch")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("1.1.1-scone_70x-SNAPSHOT", s("1.1.0-scone_70x-SNAPSHOT"))

    def test_get_next_version__calver_new_day(self):
        build_pom_content = self._get_build_pom("calver")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("%s.1-whatever-this-is" % self._today(), s("3.2.0-whatever-this-is"))

    def test_get_next_version__calver_new_day_take_two(self):
        build_pom_content = self._get_build_pom("calver")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("%s.1-whatever-this-is" % self._today(), s("20200320.1-whatever-this-is"))

    def test_get_next_version__calver_same_day(self):
        build_pom_content = self._get_build_pom("calver")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("%s.2-whatever-this-is" % self._today(), s("%s.1-whatever-this-is" % self._today()))

    def test_get_next_version__calver_same_day_with_lots_of_updates(self):
        build_pom_content = self._get_build_pom("calver")
        s = version.get_version_increment_strategy(build_pom_content)
        self.assertEqual("%s.10-whatever-this-is" % self._today(), s("%s.9-whatever-this-is" % self._today()))

    def test_unknown_version_increment_strategy(self):
        build_pom_content = self._get_build_pom("lucy in the sky with diamonds")
        with self.assertRaises(Exception) as ctx:
            version.get_version_increment_strategy(build_pom_content)

        self.assertIn("Unknown version increment strategy", str(ctx.exception))
        self.assertIn("lucy in the sky with diamonds", str(ctx.exception))
        self.assertIn("valid strategies are", str(ctx.exception))
        self.assertIn("('major', 'minor', 'patch', 'calver')", str(ctx.exception))

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

    def _today(self):
        return datetime.now(timezone.utc).strftime('%Y%m%d')


if __name__ == '__main__':
    unittest.main()

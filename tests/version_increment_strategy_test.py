"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from common import version_increment_strategy as vis
from datetime import datetime, timezone


class VersionIncrementStrategyTest(unittest.TestCase):

    def test_major_version(self):
        s = vis.get_version_increment_strategy("major")

        self.assertEqual("1.0.0", s.get_next_release_version("1.0.0"))
        self.assertEqual("1.0.0", s.get_next_release_version("1.0.0-SNAPSHOT"))
        self.assertEqual("1.2.0", s.get_next_release_version("1.2.0-SNAPSHOT"))
        self.assertEqual("1.0.5", s.get_next_release_version("1.0.5-SNAPSHOT"))
        self.assertEqual("1.0.5-qual1", s.get_next_release_version("1.0.5-qual1-SNAPSHOT"))

        self.assertEqual("2.0.0-SNAPSHOT", s.get_next_development_version("1.0.0-SNAPSHOT"))
        self.assertEqual("2.0.0-SNAPSHOT", s.get_next_development_version("1.0.0"))
        self.assertEqual("2.0.0-SNAPSHOT", s.get_next_development_version("1.2.0"))
        self.assertEqual("2.0.0-SNAPSHOT", s.get_next_development_version("1.0.5"))
        self.assertEqual("2.0.0-qual1-SNAPSHOT", s.get_next_development_version("1.9.99-qual1"))

    def test_minor_version(self):
        s = vis.get_version_increment_strategy("minor")

        self.assertEqual("1.0.0", s.get_next_release_version("1.0.0"))
        self.assertEqual("1.0.1", s.get_next_release_version("1.0.1-SNAPSHOT"))
        self.assertEqual("1.1.1", s.get_next_release_version("1.1.1-SNAPSHOT"))
        self.assertEqual("1.10.1", s.get_next_release_version("1.10.1-SNAPSHOT"))
        self.assertEqual("1.0.99-qual23", s.get_next_release_version("1.0.99-qual23-SNAPSHOT"))

        self.assertEqual("1.1.0-SNAPSHOT", s.get_next_development_version("1.0.0-SNAPSHOT"))
        self.assertEqual("1.1.0-SNAPSHOT", s.get_next_development_version("1.0.0"))
        self.assertEqual("1.1.0-SNAPSHOT", s.get_next_development_version("1.0.1"))
        self.assertEqual("1.1.0-SNAPSHOT", s.get_next_development_version("1.0.9"))
        self.assertEqual("1.2.0-qual1-SNAPSHOT", s.get_next_development_version("1.1.99-qual1"))

    def test_patch_version(self):
        s = vis.get_version_increment_strategy("patch")

        self.assertEqual("1.0.1", s.get_next_release_version("1.0.1"))
        self.assertEqual("1.0.1", s.get_next_release_version("1.0.1-SNAPSHOT"))
        self.assertEqual("1.1.1", s.get_next_release_version("1.1.1-SNAPSHOT"))
        self.assertEqual("1.0.9", s.get_next_release_version("1.0.9-SNAPSHOT"))
        self.assertEqual("1.0.99-qual23", s.get_next_release_version("1.0.99-qual23-SNAPSHOT"))

        self.assertEqual("1.0.1-SNAPSHOT", s.get_next_development_version("1.0.0-SNAPSHOT"))
        self.assertEqual("1.0.9-SNAPSHOT", s.get_next_development_version("1.0.8"))
        self.assertEqual("1.1.100-SNAPSHOT", s.get_next_development_version("1.1.99"))
        self.assertEqual("1.2.1-qual1-SNAPSHOT", s.get_next_development_version("1.2.0-qual1"))

    def test_calver_version(self):
        s = vis.get_version_increment_strategy("calver")

        self.assertEqual("%s.1" % _today(), s.get_next_release_version("0-SNAPSHOT"))
        self.assertEqual("%s.1" % _today(), s.get_next_release_version("0"))
        self.assertEqual("%s.1-qual" % _today(), s.get_next_release_version("0-qual-SNAPSHOT"))
        self.assertEqual("%s.1-qual" % _today(), s.get_next_release_version("0-qual"))
        self.assertEqual("%s.3" % _today(), s.get_next_release_version("%s.2-SNAPSHOT" % _today()))

        self.assertEqual("%s.1-SNAPSHOT" % _today(), s.get_next_development_version("3.2.0"))
        self.assertEqual("%s.1-SNAPSHOT" % _today(), s.get_next_development_version("20200320.1"))
        self.assertEqual("%s.2-SNAPSHOT" % _today(), s.get_next_development_version("%s.1" % _today()))
        self.assertEqual("%s.10-SNAPSHOT" % _today(), s.get_next_development_version("%s.9" % _today()))

        self.assertEqual("%s.10-foo-blah-SNAPSHOT" % _today(), s.get_next_development_version("%s.9-foo-blah" % _today()))
        self.assertEqual("%s.10-foo-blah-SNAPSHOT" % _today(), s.get_next_development_version("%s.9-foo-blah-SNAPSHOT" % _today()))

    def test_unknown_version_increment_strategy(self):
        with self.assertRaises(Exception) as ctx:
            vis.get_version_increment_strategy("lucy in the sky with diamonds")

        self.assertIn("Unknown version increment strategy", str(ctx.exception))
        self.assertIn("lucy in the sky with diamonds", str(ctx.exception))
        self.assertIn("valid strategies are", str(ctx.exception))
        self.assertIn("('major', 'minor', 'patch', 'calver')", str(ctx.exception))

    def test_rel_qualifier_increment_strategy(self):
        s = vis.get_rel_qualifier_increment_strategy(None)
        self.assertEqual("0.0.0-rel1", s.get_next_release_version("1.0.0-SNAPSHOT"))
        self.assertEqual("1.0.0-SNAPSHOT", s.get_next_development_version("1.0.0-SNAPSHOT"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3")
        self.assertEqual("1.2.3-rel1", s.get_next_release_version("1.2.4-SNAPSHOT"))
        self.assertEqual("1.2.4-SNAPSHOT", s.get_next_development_version("1.2.4"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel1")
        self.assertEqual("1.2.3-rel2", s.get_next_release_version("1.2.4-SNAPSHOT"))
        self.assertEqual("1.2.4-SNAPSHOT", s.get_next_development_version("1.2.4-SNAPSHOT"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel9")
        self.assertEqual("1.2.3-rel10", s.get_next_release_version("1.2.4-SNAPSHOT"))
        self.assertEqual("1.2.4-SNAPSHOT", s.get_next_development_version("1.2.4-SNAPSHOT"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel10")
        self.assertEqual("1.2.3-rel11", s.get_next_release_version("1.2.4-SNAPSHOT"))
        self.assertEqual("1.2.4-SNAPSHOT", s.get_next_development_version("1.2.4-SNAPSHOT"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel99")
        self.assertEqual("1.2.3-rel100", s.get_next_release_version("1.2.4-SNAPSHOT"))
        self.assertEqual("1.2.4-SNAPSHOT", s.get_next_development_version("1.2.4-SNAPSHOT"))

    def test_rel_qualifier_increment_strategy__multiple_qualifiers(self):
        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel1-foo22")
        self.assertEqual("1.2.3-rel2-foo22", s.get_next_release_version("foo"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel9-foo22")
        self.assertEqual("1.2.3-rel10-foo22", s.get_next_release_version("foo"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel99-foo22-blah1")
        self.assertEqual("1.2.3-rel100-foo22-blah1", s.get_next_release_version("foo"))

    def test_rel_qualifier_increment_strategy__last_rel_qualifier_uses_old_dash_number_syntax(self):
        # we used to use rel-<num>, for example rel-1, rel-2 etc
        # we switched this to rel<num> (so rel1, rel2 etc) so that '-' is only
        # used as a separator between version qualifiers: 1.0.0-rel1-SNAPSHOT
        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel-1")
        self.assertEqual("1.2.3-rel2", s.get_next_release_version("blah"))

        s = vis.get_rel_qualifier_increment_strategy("1.2.3-rel-10")
        self.assertEqual("1.2.3-rel11", s.get_next_release_version("blah"))


def _today():
    return datetime.now(timezone.utc).strftime('%Y%m%d')


if __name__ == '__main__':
    unittest.main()

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import argsupport
from crawl import bazel
import unittest

PASTRY_PACKAGES = ["projects/libs/pastry/abstractions", 
                  "projects/libs/pastry/pastry-metrics",]

ZK_CONNECT_PACKAGES = ["projects/libs/servicelibs/zk-connect",]

GRAIL_PACKAGES = ["projects/libs/servicelibs/grail/grail-admin-api",
                  "projects/libs/servicelibs/grail/grail-admin-impl",]

ALL_PACKAGES_DICT = {"projects/libs" : PASTRY_PACKAGES + ZK_CONNECT_PACKAGES + GRAIL_PACKAGES,
                     "projects/libs/servicelibs" : ZK_CONNECT_PACKAGES + GRAIL_PACKAGES,
                     "projects/libs/pastry" : PASTRY_PACKAGES,
                     "projects/libs/servicelibs/zk-connect" : ZK_CONNECT_PACKAGES,
                     "projects/libs/servicelibs/grail" : GRAIL_PACKAGES,}

class ArgSupportTest(unittest.TestCase):

    def setUp(self):
        bazel.query_all_artifact_packages = lambda root, target_pattern, verbose: ALL_PACKAGES_DICT[target_pattern]

    def test_get_all_packages__single_package(self):
        packages = argsupport.get_all_packages("root", "projects/libs/pastry")

        self.assertIn("projects/libs/pastry/abstractions", packages)
        self.assertIn("projects/libs/pastry/pastry-metrics", packages)
        self.assertNotIn("projects/libs/servicelibs/zk-connect", packages)

    def test_get_all_packages__single_package__label_syntax(self):
        packages = argsupport.get_all_packages("root", "//projects/libs/servicelibs/...")

        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertIn("projects/libs/servicelibs/zk-connect", packages)

    def test_get_all_packages__single_package__with_exlusion(self):
        packages_str = "projects/libs,-projects/libs/pastry"

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertIn("projects/libs/servicelibs/zk-connect", packages)
        self.assertNotIn("projects/libs/pastry/abstractions", packages)
        self.assertNotIn("projects/libs/pastry/pastry-metrics", packages)

    def test_get_all_packages__single_package__with_exlusion_mixed_label_syntax(self):
        packages_str = "projects/libs,-//projects/libs/pastry"

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertIn("projects/libs/servicelibs/zk-connect", packages)
        self.assertNotIn("projects/libs/pastry/abstractions", packages)
        self.assertNotIn("projects/libs/pastry/pastry-metrics", packages)

    def test_get_all_packages__multiple_packages(self):
        packages_str = "projects/libs/servicelibs/grail,projects/libs/servicelibs/zk-connect"

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertIn("projects/libs/servicelibs/zk-connect", packages)

    def test_get_all_packages__multiple_packages__no_duplicates(self):
        packages_str = "projects/libs/pastry,projects/libs/servicelibs/zk-connect,projects/libs,projects/libs/servicelibs"

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/pastry/abstractions", packages)
        self.assertIn("projects/libs/pastry/pastry-metrics", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/zk-connect", packages)
        self.assertIn("projects/libs/pastry/abstractions", packages)
        # ensure no duplicates:
        num_packages = len(PASTRY_PACKAGES) + len(ZK_CONNECT_PACKAGES) + len(GRAIL_PACKAGES)
        self.assertEqual(num_packages, len(packages), "Expected %i packages but got %i: %s" % (num_packages, len(packages), packages))

    def test_get_all_packages__multiple_packages__spaces_are_trimmed(self):
        packages_str = " projects/libs/servicelibs,  -projects/libs/servicelibs/zk-connect ,  projects/libs/pastry  "

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/pastry/abstractions", packages)
        self.assertIn("projects/libs/pastry/pastry-metrics", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertNotIn("projects/libs/servicelibs/zk-connect", packages)

    def test_get_all_packages__multiple_packages__multiple_exclusions(self):
        packages_str = "projects/libs,-projects/libs/servicelibs/zk-connect,-projects/libs/servicelibs/grail"

        packages = argsupport.get_all_packages("root", packages_str)

        self.assertIn("projects/libs/pastry/abstractions", packages)
        self.assertIn("projects/libs/pastry/pastry-metrics", packages)
        self.assertNotIn("projects/libs/servicelibs/grail/grail-admin-api", packages)
        self.assertNotIn("projects/libs/servicelibs/grail/grail-admin-impl", packages)
        self.assertNotIn("projects/libs/servicelibs/zk-connect", packages)
        
if __name__ == '__main__':
    unittest.main()

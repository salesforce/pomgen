"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import unittest
from crawl.bazel import _ensure_unique_deps
from crawl.bazel import target_pattern_to_path

class BazelTest(unittest.TestCase):

    def test_target_pattern_to_path(self):
        """
        Tests for bazel.target_pattern_to_path.
        """
        self.assertEqual("foo/blah", target_pattern_to_path("//foo/blah"))
        self.assertEqual("foo/blah", target_pattern_to_path("/foo/blah"))
        self.assertEqual("foo/blah", target_pattern_to_path("foo/blah:target_name"))
        self.assertEqual("foo/blah", target_pattern_to_path("foo/blah/..."))
        self.assertEqual("foo/blah", target_pattern_to_path("foo/blah"))

    def test_ensure_unique_deps(self):
        """
        Tests for bazel._ensure_unique_deps
        """
        self.assertEqual(["//a", "//b", "//c"],
                          _ensure_unique_deps(["//a", "//b", "//c", "//a"]))

if __name__ == '__main__':
    unittest.main()

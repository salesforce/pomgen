"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import crawl.bazel as bazel
import unittest


class BazelTest(unittest.TestCase):


    def test_ensure_unique_deps(self):
        """
        Tests for bazel._ensure_unique_deps
        """
        self.assertEqual(["//a", "//b", "//c"],
                          bazel._ensure_unique_deps(["//a", "//b", "//c", "//a"]))



if __name__ == '__main__':
    unittest.main()

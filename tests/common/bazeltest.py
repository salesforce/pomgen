"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import common.bazel as bazel
import common.label as label
import common.genmode as genmode
import crawl.buildpom as buildpom
import unittest


class BazelTest(unittest.TestCase):


    def test_ensure_unique_deps(self):
        """
        Tests for bazel._ensure_unique_deps
        """
        self.assertEqual(
            ["//a", "//b", "//c"],
            bazel._ensure_unique_deps(["//a", "//b", "//c", "//a"]))

    def test_remove_package_private_labels(self):
        package = "a/b/c"
        art = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                        generation_mode=genmode.DYNAMIC)
        l1 = label.Label(package)
        l2 = label.Label("%s:foo" % package)
        l3 = label.Label("//something_else:foo")
        l4 = label.Label("@maven_install//:guava")

        labels = bazel._remove_package_private_labels([l1, l2, l3, l4], art)

        self.assertEqual([l3, l4], labels)

    def test_remove_package_private_labels__skip_mode_allows_them(self):
        package = "a/b/c"
        art = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                        generation_mode=genmode.SKIP)
        l1 = label.Label(package)
        l2 = label.Label("%s:foo" % package)
        l3 = label.Label("//something_else:foo")
        l4 = label.Label("@maven_install//:guava")

        labels = bazel._remove_package_private_labels([l1, l2, l3, l4], art)

        self.assertEqual([l1, l2, l3, l4], labels)


if __name__ == '__main__':
    unittest.main()

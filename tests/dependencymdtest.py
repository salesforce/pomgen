"""
Copyright (c) 2021, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import dependency
from crawl import dependencymd as dependencymdmod
import unittest


class DependencyMetadataTest(unittest.TestCase):

    def test_register_transitives(self):
        dependencymd = dependencymdmod.DependencyMetadata()
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven1")
        dep2 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven2")
        transitives = (dependency.new_dep_from_maven_art_str("t1:a1:v1", "foo"))

        dependencymd.register_transitives(dep1, transitives)
        dependencymd.register_transitives(dep2, transitives)

        self.assertEqual(transitives, dependencymd.get_transitive_closure(dep1))
        self.assertEqual(transitives, dependencymd.get_transitive_closure(dep2))

    def test_register_exclusions(self):
        dependencymd = dependencymdmod.DependencyMetadata()
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven1")
        dep2 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven2")
        exclusions = (dependency.new_dep_from_maven_art_str("t1:a1:v1", "foo"))

        dependencymd.register_exclusions(dep1, exclusions)
        dependencymd.register_exclusions(dep2, exclusions)

        self.assertEqual(exclusions, dependencymd.get_transitive_exclusions(dep1))
        self.assertEqual(exclusions, dependencymd.get_transitive_exclusions(dep2))


if __name__ == '__main__':
    unittest.main()


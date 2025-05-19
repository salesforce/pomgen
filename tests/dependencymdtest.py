"""
Copyright (c) 2021, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import buildpom
from crawl import dependency
from crawl import dependencymd as dependencymdmod
import unittest


class DependencyMetadataTest(unittest.TestCase):

    def test_register_transitives(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven1")
        dep2 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven2")
        transitives = (dependency.new_dep_from_maven_art_str("t1:a1:v1", "foo"))

        dependencymd.register_transitives(dep1, transitives)
        dependencymd.register_transitives(dep2, transitives)

        self.assertEqual(transitives, dependencymd.get_transitive_closure(dep1))
        self.assertEqual(transitives, dependencymd.get_transitive_closure(dep2))

    def test_get_classifier__none(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        ext_dep = dependency.new_dep_from_maven_art_str("g1:a1:pack:class:2.0,0", "m1")
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0")
        int_dep = dependency.new_dep_from_maven_artifact_def(art_def, "t1")

        self.assertEqual("class", dependencymd.get_classifier(ext_dep))
        self.assertIsNone(dependencymd.get_classifier(int_dep))

    def test_get_classifier__set_globally(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier="foo22")
        ext_dep = dependency.new_dep_from_maven_art_str("g1:a1:2.0,0", "m1")
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0")
        int_dep = dependency.new_dep_from_maven_artifact_def(art_def, "t1")

        self.assertIsNone(dependencymd.get_classifier(ext_dep))
        self.assertEqual("foo22", dependencymd.get_classifier(int_dep))


if __name__ == '__main__':
    unittest.main()


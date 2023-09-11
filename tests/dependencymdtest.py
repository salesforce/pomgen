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

    def test_register_exclusions(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven1")
        dep2 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "maven2")
        exclusions = (dependency.new_dep_from_maven_art_str("t1:a1:v1", "foo"))

        dependencymd.register_exclusions(dep1, exclusions)
        dependencymd.register_exclusions(dep2, exclusions)

        self.assertEqual(exclusions, dependencymd.get_transitive_exclusions(dep1))
        self.assertEqual(exclusions, dependencymd.get_transitive_exclusions(dep2))

    def test_get_ancestors(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "m")
        dep2 = dependency.new_dep_from_maven_art_str("g2:a1:v1", "m")
        dep3 = dependency.new_dep_from_maven_art_str("g3:a1:v1", "m")
        child_dep1 = dependency.new_dep_from_maven_art_str("t1:a1:v1", "m")
        child_dep2 = dependency.new_dep_from_maven_art_str("t2:a1:v1", "m")
        child_dep3 = dependency.new_dep_from_maven_art_str("t3:a1:v1", "m")
        dep1_transitives = [child_dep1, child_dep2]
        dep2_transitives = [child_dep2, child_dep3]

        dependencymd.register_transitives(dep1, dep1_transitives)
        dependencymd.register_transitives(dep2, dep2_transitives)

        self.assertEqual([dep1], dependencymd.get_ancestors(child_dep1))
        self.assertEqual([dep1, dep2], dependencymd.get_ancestors(child_dep2))
        self.assertEqual([dep2], dependencymd.get_ancestors(child_dep3))
        self.assertEqual([], dependencymd.get_ancestors(dep3))

    def test_get_ancestors__is_scoped_by_maven_install_rule(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        dep1 = dependency.new_dep_from_maven_art_str("g1:a1:v1", "m1")
        dep2 = dependency.new_dep_from_maven_art_str("g2:a1:v1", "m2")
        child_dep1 = dependency.new_dep_from_maven_art_str("t1:a1:v1", "m1")
        child_dep2 = dependency.new_dep_from_maven_art_str("t1:a1:v1", "m2")
        child_dep3 = dependency.new_dep_from_maven_art_str("t2:a1:v1", "m2")
        dep1_transitives = [child_dep1,]
        dep2_transitives = [child_dep2, child_dep3]

        dependencymd.register_transitives(dep1, dep1_transitives)
        dependencymd.register_transitives(dep2, dep2_transitives)

        self.assertEqual([dep1], dependencymd.get_ancestors(child_dep1))
        self.assertEqual([dep2], dependencymd.get_ancestors(child_dep2))
        self.assertEqual([dep2], dependencymd.get_ancestors(child_dep3))

    def test_get_classifier__none(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier=None)
        ext_dep = dependency.new_dep_from_maven_art_str("g1:a1:pack:class:2.0,0", "m1")
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0")
        int_dep = dependency.new_dep_from_maven_artifact_def(art_def, None)

        self.assertEqual("class", dependencymd.get_classifier(ext_dep))
        self.assertIsNone(dependencymd.get_classifier(int_dep))

    def test_get_classifier__set_globally(self):
        dependencymd = dependencymdmod.DependencyMetadata(jar_artifact_classifier="foo22")
        ext_dep = dependency.new_dep_from_maven_art_str("g1:a1:2.0,0", "m1")
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0")
        int_dep = dependency.new_dep_from_maven_artifact_def(art_def, None)

        self.assertIsNone(dependencymd.get_classifier(ext_dep))
        self.assertEqual("foo22", dependencymd.get_classifier(int_dep))


if __name__ == '__main__':
    unittest.main()


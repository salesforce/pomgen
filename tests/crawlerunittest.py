"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import pomgenmode
from crawl import buildpom
from crawl import crawler as crawlerm
from crawl import dependency
import os
import unittest

GROUP_ID = "group"
POM_TEMPLATE_FILE = "foo.template"

class CrawlerUnitTest(unittest.TestCase):
    """
    crawler tests that do not require any file-system setup.
    """

    def test_dependencies_with_skip_mode(self):
        """
        the artifact a1 references the artifact x1 as a dep:
        a1 -> x1
        x1 has pom generation mode set to "skip"
        x1's deps are added to a1's deps
        """
        parent_node = self._build_node("a1", "a/b/c",
                                       pom_generation_mode=pomgenmode.DYNAMIC)
        node = self._build_node("x1", "x/y/z",
                                pom_generation_mode=pomgenmode.SKIP,
                                parent_node=parent_node)
        parent_node.children = (node,)
        crawler = crawlerm.Crawler(workspace=None, pom_template=None)
        # setup some other deps
        guava = self._get_3rdparty_dep("com.google:guava:20.0", "guava")
        self._associate_dep(crawler, parent_node, guava)
        force = self._get_3rdparty_dep("com.force:common:1.0.0", "force")
        self._associate_dep(crawler, node, force)
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (node,)
        # sanity - the force dep is not references by the a1 artifact
        parent_node_deps = self._get_associated_deps(crawler, parent_node)
        self.assertNotIn(force, parent_node_deps)

        # run the logic that pushes deps owned by "skip" artifacts up
        crawler._push_transitives_to_parent()

        parent_node_deps = self._get_associated_deps(crawler, parent_node)
        self.assertEqual(2, len(parent_node_deps))
        self.assertIn(guava, parent_node_deps)
        self.assertIn(force, parent_node_deps)

    def test_compute_transitive_closure(self):
        """
        a1 -> a2 -> a3
        a3 has ext deps: d1, d2
        a2 has ext deps d3, d4
        a1 has ext deps d5

        the expected transitive closure of deps are:
        a3: d1, d2
        a2: d3, d4, d1, d2 (a3 also, but not part of this test)
        a1: d5, d3, d4, d1, d2 (a2 also, but not part of this test)
        """
        a1_node = self._build_node("a1", "a/b/c")
        a2_node = self._build_node("a2", "d/e/f", parent_node=a1_node)
        a1_node.children = (a2_node,)
        a3_node = self._build_node("a3", "g/h/i", parent_node=a2_node)
        a2_node.children = (a3_node,)
        crawler = crawlerm.Crawler(workspace=None, pom_template=None)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        self._associate_dep(crawler, a3_node, (d1, d2))
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        self._associate_dep(crawler, a2_node, (d3, d4))
        d5 = self._get_3rdparty_dep("com:d5:1.0.0", "d5")
        self._associate_dep(crawler, a1_node, d5)
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(2, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(d2, a3_deps[1])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(4, len(a2_deps))
        self.assertEqual(d3, a2_deps[0])
        self.assertEqual(d4, a2_deps[1])
        self.assertEqual(d1, a2_deps[2])
        self.assertEqual(d2, a2_deps[3])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(5, len(a1_deps))
        self.assertEqual(d5, a1_deps[0])
        self.assertEqual(d3, a1_deps[1])
        self.assertEqual(d4, a1_deps[2])
        self.assertEqual(d1, a1_deps[3])
        self.assertEqual(d2, a1_deps[4])

    def test_compute_transitive_closure__duplicate_deps(self):
        """
        a1 -> a2 -> a3
        a3 has ext deps: d1, d2
        a2 has ext deps d1, d2, d3
        a1 has ext deps d1, d4

        the expected transitive closure of deps are:
        a3: d1, d2
        a2: d1, d2, d3 (a3 also, but not part of this test)
        a1: d1, d4, d2, d3 (a2 also, but not part of this test)
        """
        a1_node = self._build_node("a1", "a/b/c")
        a2_node = self._build_node("a2", "d/e/f", parent_node=a1_node)
        a1_node.children = (a2_node,)
        a3_node = self._build_node("a3", "g/h/i", parent_node=a2_node)
        a2_node.children = (a3_node,)
        crawler = crawlerm.Crawler(workspace=None, pom_template=None)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        self._associate_dep(crawler, a3_node, (d1, d2))
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        self._associate_dep(crawler, a2_node, (d1, d2, d3))
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        self._associate_dep(crawler, a1_node, (d1, d4))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()
        print(target_to_all_deps)

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(2, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(d2, a3_deps[1])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(3, len(a2_deps))
        self.assertEqual(d1, a2_deps[0])
        self.assertEqual(d2, a2_deps[1])
        self.assertEqual(d3, a2_deps[2])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(4, len(a1_deps))
        self.assertEqual(d1, a1_deps[0])
        self.assertEqual(d4, a1_deps[1])
        self.assertEqual(d2, a1_deps[2])
        self.assertEqual(d3, a1_deps[3])

    def test_compute_transitive_closure__multiple_leaf_nodes(self):
        """
        a1 references both a2 and a3
        a3 has ext deps: d1, d2
        a2 has ext deps d1, d3
        a1 has ext deps d4

        the expected transitive closure of deps are:
        a3: d1, d2
        a2: d1, d3
        a1: d4, d1, d3, d2 (a2 and a3 also, but not part of this test)
        """
        a1_node = self._build_node("a1", "a/b/c")
        a2_node = self._build_node("a2", "d/e/f", parent_node=a1_node)
        a3_node = self._build_node("a3", "g/h/i", parent_node=a1_node)
        a1_node.children = (a2_node, a3_node,)
        crawler = crawlerm.Crawler(workspace=None, pom_template=None)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        self._associate_dep(crawler, a3_node, (d1, d2))
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        self._associate_dep(crawler, a2_node, (d1, d3))
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        self._associate_dep(crawler, a1_node, (d4,))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a2_node, a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(2, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(d2, a3_deps[1])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(2, len(a2_deps))
        self.assertEqual(d1, a2_deps[0])
        self.assertEqual(d3, a2_deps[1])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(4, len(a1_deps))
        self.assertEqual(d4, a1_deps[0])
        self.assertEqual(d1, a1_deps[1])
        self.assertEqual(d3, a1_deps[2])
        self.assertEqual(d2, a1_deps[3])

    def test_compute_transitive_closure__multiple_parent_nodes(self):
        """
        a1 references a10
        a2 also references a10
        a10 has ext deps: d10
        a2 has ext deps d2
        a1 has ext deps d1

        the expected transitive closure of deps are:
        a10: d10
        a2: d2, d10
        a1: d1, d10
        """
        a1_node = self._build_node("a1", "d/e/f", parent_node=None)
        a2_node = self._build_node("a2", "g/h/i", parent_node=None)
        a10_node = self._build_node("a10", "a/b/c")
        a10_node.parents = (a1_node, a2_node,)
        a1_node.children = (a10_node,)
        a2_node.children = (a10_node,)
        crawler = crawlerm.Crawler(workspace=None, pom_template=None)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        d10 = self._get_3rdparty_dep("com:d10:1.0.0", "d10")
        self._associate_dep(crawler, a10_node, (d10,))
        self._associate_dep(crawler, a2_node, (d2))
        self._associate_dep(crawler, a1_node, (d1,))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a10_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a10_deps = self._get_deps_for_node(a10_node, target_to_all_deps)        
        self.assertEqual(1, len(a10_deps))
        self.assertEqual(d10, a10_deps[0])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)        
        self.assertEqual(2, len(a2_deps))
        self.assertEqual(d2, a2_deps[0])
        self.assertEqual(d10, a2_deps[1])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)        
        self.assertEqual(2, len(a1_deps))
        self.assertEqual(d1, a1_deps[0])
        self.assertEqual(d10, a1_deps[1])

    def _build_node(self, artifact_id, bazel_package,
                    pom_generation_mode=pomgenmode.DYNAMIC,
                    parent_node=None):
        art_def = buildpom.MavenArtifactDef(
            "g1", artifact_id, "1.0.0", bazel_package=bazel_package,
            pom_generation_mode=pom_generation_mode)
        dep = dependency.new_dep_from_maven_artifact_def(art_def)
        return crawlerm.Node(parent=parent_node, artifact_def=art_def, dependency=dep)

    def _get_associated_deps(self, crawler, node):
        return self._get_deps_for_node(node, crawler.target_to_dependencies)

    def _get_deps_for_node(self, node, target_to_deps):
        target_key = crawlerm.Crawler._get_target_key(node.artifact_def.bazel_package, node.dependency)
        return target_to_deps[target_key]

    def _associate_dep(self, crawler, node, dep):
        target_key = crawlerm.Crawler._get_target_key(node.artifact_def.bazel_package, node.dependency)
        deps_list = dep if isinstance(dep, (list, tuple)) else [dep]
        if target_key in crawler.target_to_dependencies:
            crawler.target_to_dependencies[target_key] += deps_list
        else:
            crawler.target_to_dependencies[target_key] = deps_list

    def _get_3rdparty_dep(self, artifact_str, name):
        return dependency.new_dep_from_maven_art_str(artifact_str, name)


if __name__ == '__main__':
    unittest.main()

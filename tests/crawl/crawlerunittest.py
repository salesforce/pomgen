"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import common.label as label
import common.genmode as genmode
import config.config as config
import crawl.artifactgenctx as artifactgenctx
import crawl.buildpom as buildpom
import crawl.crawler as crawlerm
import common.manifestcontent as manifestcontent
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import generate.impl.pom.dependency as dependency
import generate.impl.pom.dependencymd as dependencymdm
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import generate.impl.pom.pomgenerationstrategy as pomgenerationstrategy
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
        strategy = self._get_strategy()
        parent_node = self._build_node("a1", "a/b/c", strategy,
                                       generation_mode=genmode.DYNAMIC)
        node = self._build_node("x1", "x/y/z", strategy,
                                generation_mode=genmode.SKIP,
                                parent_node=parent_node)
        parent_node.children = (node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
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
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a1_node.children = (a2_node,)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a2_node)
        a2_node.children = (a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)

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
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a1_node.children = (a2_node,)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a2_node)
        a2_node.children = (a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
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
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a1_node)
        a1_node.children = (a2_node, a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
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
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "d/e/f", strategy, parent_node=None)
        a2_node = self._build_node("a2", "g/h/i", strategy, parent_node=None)
        a10_node = self._build_node("a10", "a/b/c", strategy, parent_node=None)
        a10_node.parents = (a1_node, a2_node,)
        a1_node.children = (a10_node,)
        a2_node.children = (a10_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)

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

    def test_compute_transitive_closure__ext_deps_with_transitives(self):
        """
        a1 references both a2 and a3
        a3 has ext deps: d1, d2
        a2 has ext deps d1, d3
        a1 has ext deps d4

        ADDITIONALLY, the ext deps have the following transitives (which are not
        listed in the BUILD file):

            d1: t1, t2
            d2: t3
            d3: (no transitives)
            d4: t4, t5

        the expected transitive closure of deps are:
        a3: d1, t1, t2, d2, t3
        a2: d1, t1, t2, d3
        a1: d4, t4, t5, d1, t1, t2, d3, d2, t3 (a2 and a3 also, but not tested)
        """
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a1_node)
        a1_node.children = (a2_node, a3_node,)
        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        t1 = self._get_3rdparty_dep("com:t1:1.0.0", "t1")
        t2 = self._get_3rdparty_dep("com:t2:1.0.0", "t2")
        strategy._dependency_md.register_transitives(d1, [t1, t2])
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        t3 = self._get_3rdparty_dep("com:t3:1.0.0", "t3")
        strategy._dependency_md.register_transitives(d2, [t3,])
        self._associate_dep(crawler, a3_node, (d1, d2))
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        self._associate_dep(crawler, a2_node, (d1, d3))
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        t4 = self._get_3rdparty_dep("com:t4:1.0.0", "t4")
        t5 = self._get_3rdparty_dep("com:t5:1.0.0", "t5")
        strategy._dependency_md.register_transitives(d4, [t4, t5])
        self._associate_dep(crawler, a1_node, (d4,))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a2_node, a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(5, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(t1, a3_deps[1])
        self.assertEqual(t2, a3_deps[2])
        self.assertEqual(d2, a3_deps[3])
        self.assertEqual(t3, a3_deps[4])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(4, len(a2_deps))
        self.assertEqual(d1, a2_deps[0])
        self.assertEqual(t1, a2_deps[1])
        self.assertEqual(t2, a2_deps[2])
        self.assertEqual(d3, a2_deps[3])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(9, len(a1_deps))
        self.assertEqual(d4, a1_deps[0])
        self.assertEqual(t4, a1_deps[1])
        self.assertEqual(t5, a1_deps[2])
        self.assertEqual(d1, a1_deps[3])
        self.assertEqual(t1, a1_deps[4])
        self.assertEqual(t2, a1_deps[5])
        self.assertEqual(d3, a1_deps[6])
        self.assertEqual(d2, a1_deps[7])
        self.assertEqual(t3, a1_deps[8])

    def test_compute_transitive_closure__ext_deps_with_same_transitives(self):
        """
        a1 references both a2 and a3
        a3 has ext deps: d1, d2
        a2 has ext deps d1, d3
        a1 has ext deps d4

        ADDITIONALLY, the ext deps have the following transitives (which are not
        listed in the BUILD file):

            d1: t1
            d2: t2
            d3: t1
            d4: t2

        the expected transitive closure of deps are:
        a3: d1, t1, d2, t2
        a2: d1, t1, d3
        a1: d4, t2, d1, t1, d3, d2 (a2 and a3 also, but not tested)
        """
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a1_node)
        a1_node.children = (a2_node, a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        t1 = self._get_3rdparty_dep("com:t1:1.0.0", "t1")
        strategy._dependency_md.register_transitives(d1, [t1,])
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        t2 = self._get_3rdparty_dep("com:t2:1.0.0", "t2")
        strategy._dependency_md.register_transitives(d2, [t2,])
        self._associate_dep(crawler, a3_node, (d1, d2))
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        strategy._dependency_md.register_transitives(d3, [t1,])
        self._associate_dep(crawler, a2_node, (d1, d3))
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        strategy._dependency_md.register_transitives(d4, [t2,])
        self._associate_dep(crawler, a1_node, (d4,))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a2_node, a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(4, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(t1, a3_deps[1])
        self.assertEqual(d2, a3_deps[2])
        self.assertEqual(t2, a3_deps[3])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(3, len(a2_deps))
        self.assertEqual(d1, a2_deps[0])
        self.assertEqual(t1, a2_deps[1])
        self.assertEqual(d3, a2_deps[2])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(6, len(a1_deps))
        self.assertEqual(d4, a1_deps[0])
        self.assertEqual(t2, a1_deps[1])
        self.assertEqual(d1, a1_deps[2])
        self.assertEqual(t1, a1_deps[3])
        self.assertEqual(d3, a1_deps[4])
        self.assertEqual(d2, a1_deps[5])

    def test_compute_transitive_closure__ext_deps_some_listed_transitives(self):
        """
        a1 references both a2 and a3
        a3 has ext deps: d1, d2, t1, d3
        a2 has ext deps t1, t3, d1
        a1 has ext deps t3, t2, d4

        ADDITIONALLY, the ext deps have the following transitives (which are not
        listed in the BUILD file):

            d1: t1, t2
            d2: t3

        the expected transitive closure of deps are:
        a3: d1, t2, d2, t3, t1, d3
        a2: t1, t3, d1, t2
        a1: t3, t2, d4, t1, d1, d2, d3 (a2 and a3 also, but not tested)
        """
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy)
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node)
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a1_node)
        a1_node.children = (a2_node, a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        # setup 3rd party deps
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        t1 = self._get_3rdparty_dep("com:t1:1.0.0", "t1")
        t2 = self._get_3rdparty_dep("com:t2:1.0.0", "t2")
        strategy._dependency_md.register_transitives(d1, [t1, t2])
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        t3 = self._get_3rdparty_dep("com:t3:1.0.0", "t3")
        strategy._dependency_md.register_transitives(d2, [t3,])
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        self._associate_dep(crawler, a3_node, (d1, d2, t1, d3))
        self._associate_dep(crawler, a2_node, (t1, t3, d1))
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        self._associate_dep(crawler, a1_node, (t3, t2, d4,))
        # setup necessary crawler state to simulate previous crawling
        crawler.leafnodes = (a2_node, a3_node,)

        target_to_all_deps = crawler._compute_transitive_closures_of_deps()

        a3_deps = self._get_deps_for_node(a3_node, target_to_all_deps)
        self.assertEqual(6, len(a3_deps))
        self.assertEqual(d1, a3_deps[0])
        self.assertEqual(t2, a3_deps[1])
        self.assertEqual(d2, a3_deps[2])
        self.assertEqual(t3, a3_deps[3])
        self.assertEqual(t1, a3_deps[4])
        self.assertEqual(d3, a3_deps[5])
        a2_deps = self._get_deps_for_node(a2_node, target_to_all_deps)
        self.assertEqual(4, len(a2_deps))
        self.assertEqual(t1, a2_deps[0])
        self.assertEqual(t3, a2_deps[1])
        self.assertEqual(d1, a2_deps[2])
        self.assertEqual(t2, a2_deps[3])
        a1_deps = self._get_deps_for_node(a1_node, target_to_all_deps)
        self.assertEqual(7, len(a1_deps))
        self.assertEqual(t3, a1_deps[0])
        self.assertEqual(t2, a1_deps[1])
        self.assertEqual(d4, a1_deps[2])
        self.assertEqual(t1, a1_deps[3])
        self.assertEqual(d1, a1_deps[4])
        self.assertEqual(d2, a1_deps[5])
        self.assertEqual(d3, a1_deps[6])

    def test_propagate_requires_release_up__single_child(self):
        """
        l1 -> l2, l2 requires release
        """
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy, library_path="l1")
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node, library_path="l2")
        a1_node.children = (a2_node,)
        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        crawler.library_to_nodes["l1"].append(a1_node)
        crawler.library_to_nodes["l2"].append(a2_node)
        crawler.library_to_artifact["l1"].append(a1_node.artifact_def)
        crawler.library_to_artifact["l2"].append(a2_node.artifact_def)

        crawler.leafnodes = (a2_node,)

        a2_node.artifact_def.requires_release = True
        a2_node.artifact_def.release_reason = "some reason"
        crawler._calculate_artifact_release_flag(force_release=False)

        self.assertTrue(a1_node.artifact_def.requires_release)
        self.assertIn("transitive", a1_node.artifact_def.release_reason)

    def test_propagate_requires_release_up__two_children(self):
        """
        l1 -> (l2, l3), l3 requires release
        """
        strategy = self._get_strategy()
        a1_node = self._build_node("a1", "a/b/c", strategy, library_path="l1")
        a2_node = self._build_node("a2", "d/e/f", strategy, parent_node=a1_node, library_path="l2")
        a3_node = self._build_node("a3", "g/h/i", strategy, parent_node=a1_node, library_path="l3")
        a1_node.children = (a2_node, a3_node,)

        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        crawler.library_to_nodes["l1"].append(a1_node)
        crawler.library_to_nodes["l2"].append(a2_node)
        crawler.library_to_nodes["l3"].append(a3_node)
        crawler.library_to_artifact["l1"].append(a1_node.artifact_def)
        crawler.library_to_artifact["l2"].append(a2_node.artifact_def)
        crawler.library_to_artifact["l3"].append(a3_node.artifact_def)

        crawler.leafnodes = (a2_node, a3_node)

        a3_node.artifact_def.requires_release = True
        a2_node.artifact_def.release_reason = "some reason"
        crawler._calculate_artifact_release_flag(force_release=False)

        self.assertTrue(a1_node.artifact_def.requires_release)
        self.assertIn("transitive", a1_node.artifact_def.release_reason)

    def test_remove_package_private_labels(self):
        package = "a/b/c"
        art = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                        generation_mode=genmode.DYNAMIC)
        l1 = label.Label(package)
        l2 = label.Label("%s:foo" % package)
        l3 = label.Label("//something_else:foo")
        l4 = label.Label("@maven_install//:guava")

        labels = crawlerm.Crawler._remove_package_private_labels([l1, l2, l3, l4], art)

        self.assertEqual([l3, l4], labels)

    def test_remove_package_private_labels__skip_mode_allows_them(self):
        package = "a/b/c"
        art = buildpom.MavenArtifactDef("g1", "a1", "1", bazel_package=package,
                                        generation_mode=genmode.SKIP)
        l1 = label.Label(package)
        l2 = label.Label("%s:foo" % package)
        l3 = label.Label("//something_else:foo")
        l4 = label.Label("@maven_install//:guava")

        labels = crawlerm.Crawler._remove_package_private_labels([l1, l2, l3, l4], art)

        self.assertEqual([l1, l2, l3, l4], labels)

    def test_register_dependencies(self):
        library_path = "projects/libs/lib"
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        strategy = self._get_strategy()
        node1 = self._build_node("art1", "projects/libs/lib/p1", strategy,
                                 library_path=library_path)
        node2 = self._build_node("art2", "projects/libs/lib/p2", strategy,
                                 library_path=library_path)
        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        crawler.library_to_nodes[library_path].append(node1)
        crawler.library_to_nodes[library_path].append(node2)
        ctx = artifactgenctx.ArtifactGenerationContext(node1.artifact_def, node1.label)
        crawler.genctxs = [ctx]
        crawler.target_to_dependencies = {node1.label: [d1,d2]}
        target_to_transitive_closure_deps = {
            node1.label: [d1, d2, d3],
            node2.label: [d4],
        }

        crawler._register_dependencies(target_to_transitive_closure_deps)

        self.assertEqual(set([d1, d2]), set(ctx.direct_dependencies))
        self.assertEqual(set([d1, d2, d3]), set(ctx.artifact_transitive_closure))
        self.assertEqual(set([d1, d2, d3, d4]), set(ctx.library_transitive_closure))

    def test_register_dependencies_with_exclusions(self):
        library_path = "projects/libs/lib"
        d1 = self._get_3rdparty_dep("com:d1:1.0.0", "d1")
        d2 = self._get_3rdparty_dep("com:d2:1.0.0", "d2")
        d3 = self._get_3rdparty_dep("com:d3:1.0.0", "d3")
        d4 = self._get_3rdparty_dep("com:d4:1.0.0", "d4")
        d5 = self._get_3rdparty_dep("com:d5:1.0.0", "d5")
        strategy = self._get_strategy()
        node1 = self._build_node("art1", "projects/libs/lib/p1", strategy,
                                 library_path=library_path)
        node2 = self._build_node("art2", "projects/libs/lib/p2", strategy,
                                 library_path=library_path)
        ws = self._get_workspace()
        crawler = crawlerm.Crawler(ws, strategy)
        crawler.library_to_nodes[library_path].append(node1)
        crawler.library_to_nodes[library_path].append(node2)
        ctx = artifactgenctx.ArtifactGenerationContext(node1.artifact_def, node1.label)
        crawler.genctxs = [ctx]
        crawler.target_to_dependencies = {node1.label: [d1,d2]}
        target_to_transitive_closure_deps = {
            node1.label: [d1, d2, d3],
            node2.label: [d4],
        }
        # add one additional dependency and exclude d2
        node1.artifact_def._emitted_dependencies = ["com:d5:1.0.0", "-com:d2",]

        crawler._register_dependencies(target_to_transitive_closure_deps)

        self.assertEqual(set([d1, d5]), set(ctx.direct_dependencies))
        self.assertEqual(set([d1, d3]), set(ctx.artifact_transitive_closure))
        self.assertEqual(set([d1, d3, d4]), set(ctx.library_transitive_closure))

    def _build_node(self, artifact_id, bazel_package, strategy,
                    generation_mode=genmode.DYNAMIC,
                    parent_node=None, library_path=None):
        art_def = buildpom.MavenArtifactDef(
            "g1", artifact_id, "1.0.0",
            bazel_package=bazel_package,
            generation_mode=generation_mode,
            library_path=library_path,
            bazel_target="t1", generation_strategy=strategy)
        
        return crawlerm.Node(parent_node, art_def, label.Label(bazel_package))

    def _get_associated_deps(self, crawler, node):
        return self._get_deps_for_node(node, crawler.target_to_dependencies)

    def _get_deps_for_node(self, node, target_to_deps):
        return target_to_deps[node.label]

    def _associate_dep(self, crawler, node, dep):
        deps_list = dep if isinstance(dep, (list, tuple)) else [dep]
        if node.label in crawler.target_to_dependencies:
            crawler.target_to_dependencies[node.label] += deps_list
        else:
            crawler.target_to_dependencies[node.label] = deps_list

    def _get_3rdparty_dep(self, artifact_str, name):
        return dependency.new_dep_from_maven_art_str(artifact_str, name)

    def _get_workspace(self):
        fac = generationstrategyfactory.GenerationStrategyFactory(
            "root", config.Config(), manifestcontent.NOOP, verbose=True)
        return workspace.Workspace("a/b/c", config.Config(), fac)

    def _get_strategy(self):
        strategy = pomgenerationstrategy.PomGenerationStrategy(
            "root", config.Config(), maveninstallinfo.NOOP,
            dependencymdm.DependencyMetadata(None),
            manifestcontent.NOOP, label_to_overridden_fq_label={}, verbose=True)
        strategy.initialize()
        return strategy


if __name__ == '__main__':
    unittest.main()

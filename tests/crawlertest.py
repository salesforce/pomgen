"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common.os_util import run_cmd
from common import maveninstallinfo
from config import exclusions
from crawl import crawler
from crawl import git
from crawl import pom as pomm
from crawl import pomcontent
from crawl import releasereason as rr
from crawl import workspace
import os
import tempfile
import unittest
from unittest.mock import patch

GROUP_ID = "group"
POM_TEMPLATE_FILE = "foo.template"

class CrawlerTest(unittest.TestCase):

    def setUp(self):
        """
        All tests start out with 3 libraries:
   
        A -> B -> C
          \-> C


        Each libray has 2 artifacts, a1 and a2. All references to other 
        libraries are through the a1 artifact. The a2 artifact does not 
        reference anything.

        The directory structure is:
           libs/<lib-root-dir>/a1/MVN-INF/BUILD.pom
           libs/<lib-root-dir>/a2/MVN-INF/BUILD.pom

        Versions:
          A: 1.0.0
          B: 2.0.0
          C: 3.0.0

        Released Versions:
          A: 0.0.1
          B: 0.0.2
          C: 0.0.3
        """
        self.repo_root_path = tempfile.mkdtemp("monorepo")
        self._add_libraries(self.repo_root_path)
        self._setup_repo(self.repo_root_path)
        self._write_all_build_pom_released(self.repo_root_path)
        self.cwd = os.getcwd()
        os.chdir(self.repo_root_path)
        ws = workspace.Workspace(self.repo_root_path,
                                 [], exclusions.src_exclusions(),
                                 maven_install_info=maveninstallinfo.NOOP,
                                 pom_content=pomcontent.NOOP)
        self.crawler = crawler.Crawler(ws, pom_template="")

    def tearDown(self):
        os.chdir(self.cwd)

    def test_setup(self):
        """
        Ensures that the test libraries have been setup correctly.
        """
        self._update_files(self.repo_root_path, ["libs/a/a1", "libs/b/a1", "libs/c/a1"])
        self._commit(self.repo_root_path) 

        result = self.crawler.crawl(["libs/a/a1"])

        # we have root nodes:
        # A_a1 - starting point
        # A_a2 - added because part of A library (but not referenced)
        # B_a2 - added because part of B library (but not referenced)
        # C_a2 - added because part of C library (but not referenced)
        self.assertEqual(4, len(result.nodes), "Unexpected root nodes: %s" % [n.artifact_def.artifact_id for n in result.nodes])

        # LIB A
        node_a_a1 = result.nodes[0]
        self.assertEqual("libs/a", node_a_a1.artifact_def.library_path)
        self.assertEqual("libs/a/a1", node_a_a1.artifact_def.bazel_package)
        self.assertEqual("1.0.0", node_a_a1.artifact_def.version)
        self.assertEqual(0, len(node_a_a1.parents))
        self.assertEqual(2, len(node_a_a1.children)) # b_a1 and c_a1

        node_a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertEqual("libs/a", node_a_a2.artifact_def.library_path)
        self.assertEqual("libs/a/a2", node_a_a2.artifact_def.bazel_package)
        self.assertEqual("1.0.0", node_a_a2.artifact_def.version)
        self.assertEqual(0, len(node_a_a2.parents))
        self.assertEqual(0, len(node_a_a2.children))

        # LIB B
        node_b_a1 = node_a_a1.children[0]
        self.assertEqual("libs/b", node_b_a1.artifact_def.library_path)
        self.assertEqual("libs/b/a1", node_b_a1.artifact_def.bazel_package)
        self.assertEqual("2.0.0", node_b_a1.artifact_def.version)
        self.assertEqual(1, len(node_b_a1.parents))
        self.assertEqual(node_a_a1, node_b_a1.parents[0])
        self.assertEqual(1, len(node_b_a1.children)) # c_a1

        node_b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b", node_b_a2.artifact_def.library_path)
        self.assertEqual("libs/b/a2", node_b_a2.artifact_def.bazel_package)
        self.assertEqual("2.0.0", node_b_a2.artifact_def.version)
        self.assertEqual(0, len(node_b_a2.parents))
        self.assertEqual(0, len(node_b_a2.children))

        # LIB C
        node_c_a1 = node_b_a1.children[0]
        self.assertEqual("libs/c", node_c_a1.artifact_def.library_path)
        self.assertEqual("libs/c/a1", node_c_a1.artifact_def.bazel_package)
        self.assertEqual("3.0.0", node_c_a1.artifact_def.version)
        self.assertEqual(2, len(node_c_a1.parents))
        self.assertEqual(node_b_a1, node_c_a1.parents[0])
        self.assertEqual(node_a_a1, node_c_a1.parents[1])
        self.assertEqual(0, len(node_c_a1.children))

        node_c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c", node_c_a2.artifact_def.library_path)
        self.assertEqual("libs/c/a2", node_c_a2.artifact_def.bazel_package)
        self.assertEqual("3.0.0", node_c_a2.artifact_def.version)
        self.assertEqual(0, len(node_c_a2.parents))
        self.assertEqual(0, len(node_c_a2.children))

        node_c_a1_from_a_a1 = node_a_a1.children[1]
        # node c_a1 reachable through a_a1 is the same instance as the node
        # reachable through node_b_a1_
        self.assertIs(node_c_a1_from_a_a1, node_c_a1)

    def test_no_lib_changed(self):
        """
        If no library changed, we do not get any pom generator instances.
        """
        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(0, len(result.pomgens))

    def test_no_lib_changed__force_release(self):
        """
        If no library changed, we do not get any pom generator instances, unless
        we use force.
        """
        result = self.crawler.crawl(["libs/a/a1"], force_release=True)

        self.assertEqual(6, len(result.pomgens))
        for p in result.pomgens:
            self.assertEqual(rr.ReleaseReason.ALWAYS,
                p.artifact_def.release_reason)

    def test_all_libs_changed(self):
        """
        All 3 libraries have changed, we end up with one pom generator for each
        artifact, each marked with the expected release reason.
        """
        self._update_files(self.repo_root_path, ["libs/a/a2", "libs/b/a2", "libs/c/a1"])
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        all = set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2", "libs/c/a1", "libs/c/a2"])
        self.assertEqual(all, set([p.artifact_def.bazel_package for p in result.pomgens]))
        for p in result.pomgens:
            self.assertEqual(rr.ReleaseReason.ARTIFACT,
                p.artifact_def.release_reason)

    def test_all_libs_changed__force_release(self):
        """
        When 'force_release' is specified, it takes precedence over any other
        release reason.
        """
        self._update_files(self.repo_root_path, ["libs/a/a2", "libs/b/a2", "libs/c/a1"])
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"], force_release=True)

        all = set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2", "libs/c/a1", "libs/c/a2"])
        self.assertEqual(all, set([p.artifact_def.bazel_package for p in result.pomgens]))
        for p in result.pomgens:
            self.assertEqual(rr.ReleaseReason.ALWAYS,
                p.artifact_def.release_reason)

    def test_all_libs_changed__dont_follow_refs(self):
        """
        All 3 libraries have changed, but explicitly disable crawling.
        """
        self._update_files(self.repo_root_path, ["libs/a/a1", "libs/b/a1", "libs/c/a1"])
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"], follow_references=False)

        self.assertEqual(set(["libs/a/a1"]),
                         set([p.artifact_def.bazel_package for p in result.pomgens]))

    def test_register_dependencies(self):
        """
        Verifies that the register_dependencies* methods are called by the
        crawler.
        """
        self._update_files(self.repo_root_path, ["libs/a/a1",])
        self._commit(self.repo_root_path)

        registered_deps = []
        registered_artifact_deps = []
        registered_library_deps = []
        import crawl.pom as pom
        register_deps_org_method = pom.TemplatePomGen.register_dependencies
        register_deps_artifact_org_method = pom.TemplatePomGen.register_dependencies_transitive_closure__artifact
        register_deps_library_org_method = pom.TemplatePomGen.register_dependencies_transitive_closure__library
        try:
            pom.TemplatePomGen.register_dependencies = lambda s, deps: registered_deps.append(list(deps))
            pom.TemplatePomGen.register_dependencies_transitive_closure__artifact = lambda s, deps: registered_artifact_deps.append(list(deps))
            pom.TemplatePomGen.register_dependencies_transitive_closure__library = lambda s, deps: registered_library_deps.append(list(deps))

            self.crawler.crawl(["libs/a/a1"],)

            self.assertTrue(len(registered_deps) > 0, "register_dependencies was not called")
            self.assertTrue(len(registered_artifact_deps) > 0, "register_dependencies_transitive_closure__artifact was not called")
            self.assertTrue(len(registered_library_deps) > 0, "register_dependencies_transitive_closure__library was not called")

        finally:
            pom.TemplatePomGen.register_dependencies = register_deps_org_method
            pom.TemplatePomGen.register_dependencies_transitive_closure__artifact = register_deps_artifact_org_method
            pom.TemplatePomGen.register_dependencies_transitive_closure__library = register_deps_library_org_method

    def test_version_references_in_pom_template(self):
        """
        Verify that monorepo artifact versions can be referenced in a pom
        template.
        """
        pom_template = """
<project>
<version>#{%s:B_a1:version}</version>
<version>#{%s:C_a1:version}</version>
</project>
"""
        self._write_file(self.repo_root_path, "libs/a/a1", "MVN-INF", 
                         POM_TEMPLATE_FILE, pom_template % (GROUP_ID, GROUP_ID))

        # this is required because poms are only compared if there's a 
        # pom.xml.released
        self._write_file(self.repo_root_path, "libs/a/a1", "MVN-INF", 
                         "pom.xml.released", """<project></project>""")

        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        pom = result.pomgens[0].gen(pomm.PomContentType.RELEASE)
        
        self.assertIn("<version>0.0.2</version>", pom)
        self.assertIn("<version>0.0.3</version>", pom)

    def test_A_a1_changed(self):
        """
        Only A's a1 changed - poms are only generated for A.
        """
        self._update_file(self.repo_root_path, "libs/a/a1", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2"]),
                          set([p.artifact_def.bazel_package for p in result.pomgens]))
        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIsNone(b_a1.artifact_def.release_reason)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIsNone(b_a2.artifact_def.release_reason)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertIsNone(c_a1.artifact_def.release_reason)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertIsNone(c_a2.artifact_def.release_reason)

    def test_A_a2_changed(self):
        """
        Only A's a2 changed - poms are only generated for A.
        """
        self._update_file(self.repo_root_path, "libs/a/a2", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2"]),
                          set([p.artifact_def.bazel_package for p in result.pomgens]))
        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIsNone(b_a1.artifact_def.release_reason)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIsNone(b_a2.artifact_def.release_reason)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertIsNone(c_a1.artifact_def.release_reason)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertIsNone(c_a2.artifact_def.release_reason)

    def test_B_a1_changed(self):
        """
        Only B's a1 changed - poms are only generated for A and B.
        """
        self._update_file(self.repo_root_path, "libs/b/a1", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2"]),
                         set([p.artifact_def.bazel_package for p in result.pomgens]))

        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIs(b_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIs(b_a2.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertIsNone(c_a1.artifact_def.release_reason)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertIsNone(c_a2.artifact_def.release_reason)

    def test_B_a2_changed(self):
        """
        Only B's a2 changed - poms are only generated for A and B.
        """
        self._update_file(self.repo_root_path, "libs/b/a2", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2"]),
                         set([p.artifact_def.bazel_package for p in result.pomgens]))

        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIs(b_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIs(b_a2.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertIsNone(c_a1.artifact_def.release_reason)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertIsNone(c_a2.artifact_def.release_reason)

    def test_C_a1_changed(self):
        """
        Only C's a1 changed - poms are generated for A, B and C (B needs to be released to bring in the changed C transitively)
        """
        self._update_file(self.repo_root_path, "libs/c/a1", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2", "libs/c/a1", "libs/c/a2"]),
                         set([p.artifact_def.bazel_package for p in result.pomgens]))

        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIs(b_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIs(b_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertEqual(c_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertEqual(c_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

    def test_C_a2_changed(self):
        """
        Only C's a2 changed - poms are generated for A, B and C (B needs to be released to bring in the changed C transitively)
        """
        self._update_file(self.repo_root_path, "libs/c/a2", "", "some-file")
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a2"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2", "libs/c/a1", "libs/c/a2"]),
                         set([p.artifact_def.bazel_package for p in result.pomgens]))

        a_a1 = self._get_node_by_bazel_package(result.nodes, "libs/a/a1")
        self.assertIs(a_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        a_a2 = self._get_node_by_bazel_package(result.nodes, "libs/a/a2")
        self.assertIs(a_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        b_a1 = a_a1.children[0]
        self.assertEqual("libs/b/a1", b_a1.artifact_def.bazel_package)
        self.assertIs(b_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        b_a2 = self._get_node_by_bazel_package(result.nodes, "libs/b/a2")
        self.assertEqual("libs/b/a2", b_a2.artifact_def.bazel_package)
        self.assertIs(b_a2.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)

        c_a1 = b_a1.children[0]
        self.assertEqual("libs/c/a1", c_a1.artifact_def.bazel_package)
        self.assertEqual(c_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)
        c_a2 = self._get_node_by_bazel_package(result.nodes, "libs/c/a2")
        self.assertEqual("libs/c/a2", c_a2.artifact_def.bazel_package)
        self.assertEqual(c_a1.artifact_def.release_reason, rr.ReleaseReason.ARTIFACT)

    def test_released_pom_exists_without_changes(self):
        """
        B a1 has a pom.xml.released file, but it has not changed.
        """
        self._write_file(self.repo_root_path, "libs/b/a1", "MVN-INF", 
                         "pom.xml.released", "<project></project>")
        self._write_file(self.repo_root_path, "libs/b/a1", "MVN-INF", 
                         POM_TEMPLATE_FILE, "<project></project>")
        self._commit(self.repo_root_path)
        released_artifact_hash = git.get_dir_hash(self.repo_root_path, ["libs/b/a1"], exclusions.src_exclusions())
        self._write_build_pom_released(self.repo_root_path, "libs/b/a1", "1.0.0", released_artifact_hash)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(0, len(result.pomgens))
        
    def test_one_lib_changed__lib_b__pom_changes_only(self):
        """
        B a2's pom changed since it was last released.
        """
        self._write_file(self.repo_root_path, "libs/b/a2", "MVN-INF", 
                         "pom.xml.released",
                         """<project> <dependencies> ... </dependencies> </project>""")
        self._write_file(self.repo_root_path, "libs/b/a2", "MVN-INF", 
                         POM_TEMPLATE_FILE, "<project></project>")
        self._commit(self.repo_root_path)
        released_artifact_hash = git.get_dir_hash(self.repo_root_path, ["libs/b/a2"], exclusions.src_exclusions())
        self._write_build_pom_released(self.repo_root_path, "libs/b/a2", "1.0.0", released_artifact_hash)

        result = self.crawler.crawl(["libs/a/a1"])

        self.assertEqual(set(["libs/a/a1", "libs/a/a2", "libs/b/a1", "libs/b/a2"]),
                          set([p.artifact_def.bazel_package for p in result.pomgens]))
        node_a_a1 = result.nodes[0]
        self.assertIs(node_a_a1.artifact_def.release_reason, rr.ReleaseReason.TRANSITIVE)
        node_b_a1 = node_a_a1.children[0]
        self.assertEqual("libs/b/a1", node_b_a1.artifact_def.bazel_package)
        self.assertIs(node_b_a1.artifact_def.release_reason, rr.ReleaseReason.POM)

    def test_pomgen_dependencies_state(self):
        """
        Verifies the dependencies set on pomgen instances.
        """
        # add one more library, D, so that C references D.
        self._add_library("D", "3.0.0", self.repo_root_path, "libs/d", deps=None)
        self._update_build_pom_deps(self.repo_root_path, "libs/c/a1", deps=["//libs/d/a1"])
        self._update_files(self.repo_root_path, ["libs/a/a2", "libs/b/a2", "libs/c/a1"])
        self._commit(self.repo_root_path)

        result = self.crawler.crawl(["libs/a/a1"])

        # LIB A A1
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/a/a1"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(2, len(dependency_paths))
        self.assertIn("libs/b/a1", dependency_paths)
        self.assertIn("libs/c/a1", dependency_paths)

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(3, len(dependency_paths))
        self.assertIn("libs/b/a1", dependency_paths)
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(5, len(dependency_paths))
        self.assertIn("libs/a/a1", dependency_paths) # own artifact included
        self.assertIn("libs/a/a2", dependency_paths) # own artifact included
        self.assertIn("libs/b/a1", dependency_paths)
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB A A2
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/a/a2"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(5, len(dependency_paths))
        self.assertIn("libs/a/a1", dependency_paths) # own artifact included
        self.assertIn("libs/a/a2", dependency_paths) # own artifact included
        self.assertIn("libs/b/a1", dependency_paths)
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB B A1
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/b/a1"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(1, len(dependency_paths))
        self.assertIn("libs/c/a1", dependency_paths)

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(2, len(dependency_paths))
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(4, len(dependency_paths))
        self.assertIn("libs/b/a1", dependency_paths) # own artifact included
        self.assertIn("libs/b/a2", dependency_paths) # own artifact included
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB B A2
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/b/a2"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(4, len(dependency_paths))
        self.assertIn("libs/b/a1", dependency_paths) # own artifact included
        self.assertIn("libs/b/a2", dependency_paths) # own artifact included
        self.assertIn("libs/c/a1", dependency_paths)
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB C A1
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/c/a1"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(1, len(dependency_paths))
        self.assertIn("libs/d/a1", dependency_paths)

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(1, len(dependency_paths))
        self.assertIn("libs/d/a1", dependency_paths)

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(3, len(dependency_paths))
        self.assertIn("libs/c/a1", dependency_paths) # own artifact included
        self.assertIn("libs/c/a2", dependency_paths) # own artifact included
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB C A2
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/c/a2"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(3, len(dependency_paths))
        self.assertIn("libs/c/a1", dependency_paths) # own artifact included
        self.assertIn("libs/c/a2", dependency_paths) # own artifact included
        self.assertIn("libs/d/a1", dependency_paths)

        # LIB D A1
        pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/d/a1"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(2, len(dependency_paths))
        self.assertIn("libs/d/a1", dependency_paths) # own artifact included
        self.assertIn("libs/d/a2", dependency_paths) # own artifact included

        # LIB D A2
        _pomgen = [p for p in result.pomgens if p.artifact_def.bazel_package == "libs/d/a2"][0]

        # direct dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of artifact dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_artifact_transitive_closure]
        self.assertEqual(0, len(dependency_paths))

        # transitive closure of library dependencies
        dependency_paths = [d.bazel_package for d in pomgen.dependencies_library_transitive_closure]
        self.assertEqual(2, len(dependency_paths))
        self.assertIn("libs/d/a1", dependency_paths) # own artifact included
        self.assertIn("libs/d/a2", dependency_paths) # own artifact included

    def _add_libraries(self, repo_root_path):
        self._add_library("C", "3.0.0", repo_root_path, "libs/c", deps=None)
        self._add_library("B", "2.0.0", repo_root_path, "libs/b", deps=["//libs/c/a1"])
        self._add_library("A", "1.0.0", repo_root_path, "libs/a",
                          deps=["//libs/b/a1", "//libs/c/a1"])

    def _write_all_build_pom_released(self, repo_root_path):
        # LIB A
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/a/a1"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/a/a1", "0.0.1", dir_hash)
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/a/a2"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/a/a2", "0.0.1", dir_hash)
        # LIB B
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/b/a1"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/b/a1", "0.0.2", dir_hash)
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/b/a2"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/b/a2", "0.0.2", dir_hash)
        # LIB C
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/c/a1"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/c/a1", "0.0.3", dir_hash)
        dir_hash = git.get_dir_hash(repo_root_path, ["libs/c/a2"], exclusions.src_exclusions())
        self._write_build_pom_released(repo_root_path, "libs/c/a2", "0.0.3", dir_hash)
        
    def _add_library(self, library_name, version, repo_root_path, lib_rel_path, deps):
        self._write_library_root(repo_root_path, lib_rel_path)

        package_rel_path = os.path.join(lib_rel_path, "a1")
        self._write_build_pom(repo_root_path, package_rel_path, library_name + "_a1", GROUP_ID, version, deps=deps)
        self._update_file(repo_root_path, package_rel_path, "MVN-INF", POM_TEMPLATE_FILE)

        package_rel_path = os.path.join(lib_rel_path, "a2")
        self._write_build_pom(repo_root_path, package_rel_path, library_name + "_a2", GROUP_ID, version, deps=None)
        self._update_file(repo_root_path, package_rel_path, "MVN-INF", POM_TEMPLATE_FILE)

    def _setup_repo(self, repo_root_path):
        run_cmd("git init .", cwd=repo_root_path)
        run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        run_cmd("git config commit.gpgsign false", cwd=repo_root_path)
        self._commit(repo_root_path)

    def _commit(self, repo_root_path):
        run_cmd("git add .", cwd=repo_root_path)
        run_cmd("git commit -m 'test commit'", cwd=repo_root_path)

    def _update_files(self, repo_root_path, package_rel_paths):
        for p in package_rel_paths:
            self._update_file(repo_root_path, p, "", "somefile")

    def _update_file(self, repo_root_path, package_rel_path, within_package_rel_path, filename):
        """
        Updates the specified file with new content.
        """
        path = os.path.join(repo_root_path, package_rel_path, within_package_rel_path, filename)
        if os.path.exists(path):
            with open(path, "r+") as f:
                content = f.read()
                content += "abc\n"
                f.seek(0)
                f.write(content)
                f.truncate()
        else:
            parent_dir = os.path.dirname(path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(path, "w") as f:
                f.write("abc\n")

    def _write_file(self, repo_root_path, package_rel_path, 
                    within_package_rel_path, filename, file_content):
        """
        Overwrites the specified file with the specified content.
        """
        path = os.path.join(repo_root_path, package_rel_path, within_package_rel_path, filename)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(file_content)

    def _write_build_pom(self, repo_root_path, package_rel_path, artifact_id, group_id, version, deps=None):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "template",
    pom_template_file = "%s",
    $deps$
)

maven_artifact_update(
    version_increment_strategy = "minor"
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        os.makedirs(path)
        content = build_pom % (artifact_id, group_id, version, POM_TEMPLATE_FILE)
        if deps is None:
            content = content.replace("$deps$", "")
        else:
            content = content.replace("$deps$", "deps=[%s]" % ",".join(['"%s"' % d for d in deps]))
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
            f.write(content)

    def _update_build_pom_deps(self, repo_root_path, package_rel_path, deps):

        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF", "BUILD.pom")
        with open(path, "r") as f:
            content = f.read()

        if "deps" in content:
            raise AssertionError("Implement me!")

        i = content.index("pom_template_file")
        j = content.index(",", i)
        content = content[:j+1] + "\ndeps=[%s]," % ",".join(['"%s"' % d for d in deps]) + content[j+1:]

        with open(path, "w") as f:
            f.write(content)

    def _write_build_pom_released(self, repo_root_path, package_rel_path, released_version, released_artifact_hash):
        build_pom_released = """
released_maven_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom.released"), "w") as f:
           f.write(build_pom_released % (released_version, released_artifact_hash))

    def _write_library_root(self, repo_root_path, package_rel_path):
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
           f.write("foo")

    def _get_node_by_bazel_package(self, nodes, bazel_package):
        for n in nodes:
            if n.artifact_def.bazel_package == bazel_package:
                return n
        else:
            self.fail("Did not find node for bazel package %s", bazel_package)


if __name__ == '__main__':
    unittest.main()

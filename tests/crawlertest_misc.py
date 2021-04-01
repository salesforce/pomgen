"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import maveninstallinfo
from config import exclusions
from crawl import crawler as crawlerm
from crawl import pom
from crawl import pomcontent
from crawl import workspace

import os
import tempfile
import unittest

GROUP_ID = "group"
POM_TEMPLATE_FILE = "foo.template"

class CrawlerTest(unittest.TestCase):
    """
    Various one-off crawler related test cases that require file-system setup.
    """

    def setUp(self):
        self.org_query_method = pom._query_dependencies
        pom._query_dependencies = lambda ws, art_def, dep: ()

    def tearDown(self):
        pom._query_dependencies = self.org_query_method

    def test_default_package_ref(self):
        """
        lib/a2 can reference lib/a1.
        """
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1"])

        ws = workspace.Workspace(repo_root_path, [],
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        crawler = crawlerm.Crawler(ws, pom_template="")

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual(1, len(result.nodes[0].children))
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)

    def test_default_package_ref_explicit(self):
        """
        lib/a2 can reference lib/a1:a1.
        """
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1:a1"])

        ws = workspace.Workspace(repo_root_path, [],
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        crawler = crawlerm.Crawler(ws, pom_template="")

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual(1, len(result.nodes[0].children))
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)

    def test_non_default_package_ref__not_allowed(self):
        """
        lib/a2 cannot reference lib/a1:foo - only default package refs
        are allowed.
        """
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1:foo"])

        ws = workspace.Workspace(repo_root_path, [],
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        crawler = crawlerm.Crawler(ws, pom_template="")

        with self.assertRaises(Exception) as ctx:
            crawler.crawl(["lib/a2"])

        self.assertIn("[lib/a2] can only reference [lib/a1]", str(ctx.exception))

    def test_non_default_package_ref__allowed_for_skip_pom_gen_mode(self):
        """
        lib/a2 is allowed to ref lib/a1:foo because lib/a1 has 
        pom_gen_mode = "skip"
        https://github.com/salesforce/pomgen/tree/master/examples/skip-artifact-generation
        """
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "skip", deps=[])
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1:foo"])

        ws = workspace.Workspace(repo_root_path, [],
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        crawler = crawlerm.Crawler(ws, pom_template="")

        crawler.crawl(["lib/a2"])

    def _add_artifact(self, repo_root_path, package_rel_path, 
                      pom_generation_mode, deps=[]):
        self._write_build_pom(repo_root_path, package_rel_path, 
                              pom_generation_mode,
                              artifact_id=os.path.basename(package_rel_path),
                              group_id="g1",
                              version="1.0.0-SNAPSHOT",
                              deps=deps)

    def _write_build_pom(self, repo_root_path, package_rel_path, pom_generation_mode, artifact_id, group_id, version, deps=None):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "%s",
    pom_template_file = "%s",
    $deps$
)

maven_artifact_update(
    version_increment_strategy = "minor"
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        os.makedirs(path)
        content = build_pom % (artifact_id, group_id, version, 
                               pom_generation_mode, POM_TEMPLATE_FILE)
        if deps is None:
            content = content.replace("$deps$", "")
        else:
            content = content.replace("$deps$", "deps=[%s]" % ",".join(['"%s"' % d for d in deps]))
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
            f.write(content)

    def _write_library_root(self, repo_root_path, package_rel_path):
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
           f.write("foo")

if __name__ == '__main__':
    unittest.main()

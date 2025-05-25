"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import maveninstallinfo
from config import config
from crawl import crawler as crawlerm
from crawl import dependencymd as dependencym
from crawl import pomcontent
from crawl import workspace
import generate.impl.pomgenerationstrategy as pomgenerationstrategy
import os
import tempfile
import unittest


GROUP_ID = "group"
POM_TEMPLATE_FILE = "foo.template"


class CrawlerTest(unittest.TestCase):
    """
    Various one-off crawler related test cases that require file-system setup.
    """

    def test_default_package_ref(self):
        """
        lib/a2 can reference lib/a1.
        """
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1"])

        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root_path,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})
        pom_template = ""
        strategy = pomgenerationstrategy.PomGenerationStrategy(ws, pom_template)
        crawler = crawlerm.Crawler(ws, strategy, pom_template)

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

        depmd = dependencym.DependencyMetadata(None)
        ws = workspace.Workspace(repo_root_path,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})
        pom_template = ""
        strategy = pomgenerationstrategy.PomGenerationStrategy(ws, pom_template)
        crawler = crawlerm.Crawler(ws, strategy, pom_template)

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual(1, len(result.nodes[0].children))
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)
        self.assertEqual("a1", result.nodes[0].children[0].artifact_def.bazel_target)

    def test_non_default_package_ref(self):
        """
        lib/a2 can reference lib/a1:foo.
        """
        depmd = dependencym.DependencyMetadata(None)
        repo_root_path = tempfile.mkdtemp("monorepo")
        self._write_library_root(repo_root_path, "lib")
        self._add_artifact(repo_root_path, "lib/a1", "template", deps=[],
                           target_name="foo")
        self._add_artifact(repo_root_path, "lib/a2", "template", deps=["//lib/a1:foo"])

        ws = workspace.Workspace(repo_root_path,
                                 self._get_config(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP,
                                 dependency_metadata=depmd,
                                 label_to_overridden_fq_label={})
        pom_template = ""
        strategy = pomgenerationstrategy.PomGenerationStrategy(ws, pom_template)
        crawler = crawlerm.Crawler(ws, strategy, pom_template)

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)
        self.assertEqual("foo", result.nodes[0].children[0].artifact_def.bazel_target)

    def _get_config(self):
        return config.Config()

    def _add_artifact(self, repo_root_path, package_rel_path,
                      pom_generation_mode,
                      target_name=None, deps=[]):
        self._write_build_pom(repo_root_path, package_rel_path, 
                              pom_generation_mode,
                              artifact_id=os.path.basename(package_rel_path),
                              group_id="g1",
                              version="1.0.0-SNAPSHOT",
                              target_name=target_name,
                              deps=deps)

    def _write_build_pom(self, repo_root_path, package_rel_path,
                         pom_generation_mode,
                         artifact_id, group_id, version,
                         target_name=None,
                         deps=None):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "%s",
    pom_template_file = "%s",
    $deps$
    $target_name$
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
            content = content.replace("$deps$", "deps=[%s]," % ",".join(['"%s"' % d for d in deps]))
        if target_name is None:
            content = content.replace("$target_name$", "")
        else:
            content = content.replace("$target_name$", "target_name = \"%s\"" % target_name)
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

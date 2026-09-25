"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import config.config as config
import crawl.crawler as crawlerm
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import generate.impl.pom.dependencymd as dependencymdm
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import generate.impl.pom.pomgenerationstrategy as pomgenerationstrategy
import os
import tempfile
import unittest


POM_TEMPLATE_FILE = "foo.template"


class CrawlerTestMisc(unittest.TestCase):
    """
    Various one-off crawler related test cases that require file-system setup.
    """
    def setup_collaborators(self, cfg=None):
        """
        The state that all tests need.
        """
        if cfg is None:
            cfg = self._get_config()
        self.repo_root_path = tempfile.mkdtemp("root")
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root_path, cfg, verbose=True)
        self.strat = self._get_strategy()
        self.ws = workspace.Workspace(self.repo_root_path, cfg, self.fac)

    def test_default_package_ref(self):
        """
        lib/a2 can reference lib/a1.
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(self.repo_root_path, "lib/a2", "template", deps=["//lib/a1"])

        crawler = crawlerm.Crawler(self.ws, verbose=True)

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual(1, len(result.nodes[0].children))
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)

    def test_default_package_ref_explicit(self):
        """
        lib/a2 can reference lib/a1:a1.
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(self.repo_root_path, "lib/a2", "template", deps=["//lib/a1:a1"])

        crawler = crawlerm.Crawler(self.ws, verbose=True)

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual(1, len(result.nodes[0].children))
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)
        self.assertEqual(None, result.nodes[0].children[0].artifact_def.bazel_target)

    def test_non_default_package_ref(self):
        """
        lib/a2 can reference lib/a1:foo.
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "template", deps=[],
                           target_name="foo")
        self._add_artifact(self.repo_root_path, "lib/a2", "template", deps=["//lib/a1:foo"])

        crawler = crawlerm.Crawler(self.ws, verbose=True)

        result = crawler.crawl(["lib/a2"])

        self.assertEqual(1, len(result.nodes))
        self.assertEqual("lib/a2", result.nodes[0].artifact_def.bazel_package)
        self.assertEqual("lib/a1", result.nodes[0].children[0].artifact_def.bazel_package)
        self.assertEqual("foo", result.nodes[0].children[0].artifact_def.bazel_target)

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)

    def _get_strategy(self):
        strategy = pomgenerationstrategy.PomGenerationStrategy(
            "root", config.Config(), maveninstallinfo.NOOP,
            dependencymdm.DependencyMetadata(None),
            label_to_overridden_fq_label={}, verbose=True)
        strategy.initialize()
        return strategy

    def _add_artifact(self, repo_root_path, package_rel_path,
                      pom_generation_mode,
                      target_name=None, deps=[],
                      excluded_dependency_paths=None):
        self._write_build_pom(repo_root_path, package_rel_path, 
                              pom_generation_mode,
                              artifact_id=os.path.basename(package_rel_path),
                              group_id="g1",
                              version="1.0.0-SNAPSHOT",
                              target_name=target_name,
                              deps=deps,
                              excluded_dependency_paths=excluded_dependency_paths)

    def _write_build_pom(self, repo_root_path, package_rel_path,
                         pom_generation_mode,
                         artifact_id, group_id, version,
                         target_name=None,
                         deps=None,
                         excluded_dependency_paths=None):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "%s",
    pom_template_file = "%s",
    $deps$
    $target_name$
    $excluded_dependency_paths$
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
        if excluded_dependency_paths is None:
            content = content.replace("$excluded_dependency_paths$", "")
        else:
            content = content.replace("$excluded_dependency_paths$", "excluded_dependency_paths=[%s]," % ",".join(['"%s"' % p for p in excluded_dependency_paths]))
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
            f.write(content)

        with open(os.path.join(path, POM_TEMPLATE_FILE), "w") as f:
            f.write("something")

    def _write_library_root(self, repo_root_path, package_rel_path):
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
           f.write("foo")


if __name__ == '__main__':
    unittest.main()

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import common.label as labelm
import config.config as config
import crawl.buildpom as buildpom
import crawl.crawler as crawlerm
import common.manifestcontent as manifestcontent
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import os
import tempfile
import unittest


GROUP_ID = "group"
POM_TEMPLATE_FILE = "foo.template"


class CrawlerTest(unittest.TestCase):
    """
    Various one-off crawler related test cases that require file-system setup.
    """
    def setUpCollaborators(self, cfg=None):
        """
        The state that all tests need.
        """
        if cfg is None:
            cfg = self._get_config()
        self.repo_root_path = tempfile.mkdtemp("root")
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root_path, cfg, manifestcontent.NOOP, verbose=True)
        self.ws = workspace.Workspace(self.repo_root_path, cfg, self.fac)

    def test_default_package_ref(self):
        """
        lib/a2 can reference lib/a1.
        """
        self.setUpCollaborators()
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
        self.setUpCollaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "template", deps=[])
        self._add_artifact(self.repo_root_path, "lib/a2", "template", deps=["//lib/a1:a1"])

        crawler = crawlerm.Crawler(self.ws, verbose=True)

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
        self.setUpCollaborators()
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

    def test_filter_label(self):
        """
        Happy path.
        """
        self.setUpCollaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "dynamic", deps=[],
                           target_name="foo")

        crawler = crawlerm.Crawler(self.ws, verbose=True)
        label = labelm.Label("//lib/a1")

        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)

        self.assertIs(label, filtered_label)

    def test_filter_label__excluded_dependency_paths(self):
        """
        Verifies that globally defined excluded dependency paths are filtered
        out.
        """
        self.setUpCollaborators(self._get_config(excluded_dependency_paths=["projects/protos/",]))
        crawler = crawlerm.Crawler(self.ws, verbose=True)
        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")

        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)
        self.assertIs(label, filtered_label) # not filtered

        label = labelm.Label("//projects/protos/grail:java_protos")
        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)
        self.assertIsNone(filtered_label) # filtered

    def test_filter_label__artifact_excluded_dependency_paths(self):
        """
        Verifies that locally defined excluded dependency paths are filtered
        out.
        """
        self.setUpCollaborators(self._get_config())
        crawler = crawlerm.Crawler(self.ws, verbose=True)
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="projects/libs/pastry",
            excluded_dependency_paths=["src/abstractions",])

        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")
        filtered_label = crawler._filter_label(label, downstream_artifact_def)
        self.assertIs(label, filtered_label) # not filtered

        label = labelm.Label("//projects/libs/pastry/src/abstractions:foo")
        filtered_label = crawler._filter_label(label, downstream_artifact_def)
        self.assertIsNone(filtered_label) # filtered

    def test_filter_label__excluded_dependency_labels(self):
        """
        Verifies that excluded dependency labels are filtered out.
        """
        self.setUpCollaborators(self._get_config(excluded_dependency_labels=["@maven//:ch_qos_logback_logback_classic",]))
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "dynamic", deps=[],
                           target_name="foo")

        crawler = crawlerm.Crawler(self.ws, verbose=True)

        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")
        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)
        self.assertIsNone(filtered_label) # filtered

        label = labelm.Label("//lib/a1")
        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)
        self.assertIs(filtered_label, label) # not filtered

        filtered_label = crawler._filter_label(label,downstream_artifact_def=None)

        self.assertIs(label, filtered_label)

    def test_src_dep_with_neverlink_enabled(self):
        """
        Verifies that no error is triggered when a dep has neverlink enabled
        and it has no BUILD.pom file.
        """
        self.setUpCollaborators()
        self._write_basic_workspace_file(self.repo_root_path)
        self._write_library_root(self.repo_root_path, "lib")
        # no BUILD.pom file
        self._write_build_file(self.repo_root_path, "lib/lombok", neverlink=True)
        crawler = crawlerm.Crawler(self.ws, verbose=True)
        label = labelm.Label("//lib/lombok")

        filtered_label = crawler._filter_label(label, downstream_artifact_def=None)

        self.assertIsNone(filtered_label)

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)

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

    def _write_build_file(self, repo_root_path, package_rel_path, neverlink=False):
        build_file = """
java_plugin(
    name = "lombok-plugin",
    generates_api = True,
    processor_class = "lombok.launch.AnnotationProcessorHider$AnnotationProcessor",
    visibility = ["//visibility:private"],
    deps = ["@nexus//:org_projectlombok_lombok"],
)

java_library(
    name = "lombok",
    neverlink = %s,
    exports = ["@nexus//:org_projectlombok_lombok"],
    exported_plugins = [":lombok-plugin"],
    visibility = ["//visibility:public"],
)
""" % (1 if neverlink else 0)

        path = os.path.join(repo_root_path, package_rel_path)
        if not os.path.exists(path):
            os.makedirs(path)
        build_file_path = os.path.join(path, "BUILD")
        with open(build_file_path, "w") as f:
           f.write(build_file)

    def _write_basic_workspace_file(self, repo_root_path):
        workspace_file = """
workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "4.1"
RULES_JVM_EXTERNAL_SHA = "f36441aa876c4f6427bfb2d1f2d723b48e9d930b62662bf723ddfb8fc80f0140"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
    url = "https://github.com/bazelbuild/rules_jvm_external/archive/%s.zip" % RULES_JVM_EXTERNAL_TAG,
)

load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven")


load("@rules_jvm_external//:repositories.bzl", "rules_jvm_external_deps")
rules_jvm_external_deps()
load("@rules_jvm_external//:setup.bzl", "rules_jvm_external_setup")
rules_jvm_external_setup()
"""
        path = os.path.join(repo_root_path)
        if not os.path.exists(path):
            os.makedirs(path)
        workspace_file_path = os.path.join(path, "WORKSPACE")
        with open(workspace_file_path, "w") as f:
           f.write(workspace_file)


if __name__ == '__main__':
    unittest.main()

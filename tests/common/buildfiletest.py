"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import common.buildfile as buildfile
import common.genmode as genmode
import common.label as labelm
import config.config as config
import crawl.buildpom as buildpom
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import generate.impl.pom.dependency as dependencym
import generate.impl.pom.dependencymd as dependencymdm
import generate.impl.pom.maveninstallinfo as maveninstallinfo
import generate.impl.pom.pomgenerationstrategy as pomgenerationstrategy
import os
import tempfile
import unittest
from unittest import mock


POM_TEMPLATE_FILE = "foo.template"


class BuildFileTest(unittest.TestCase):

    def test_load_dependencies__no_deps(self):
        artifact_def = buildpom.MavenArtifactDef("g1", "a2", "1.2.3", bazel_package="pack1")
        artifact_def = buildpom._augment_art_def_values(
            artifact_def, None, "pack1", "MVN-INF", None, None,
            genmode.TEMPLATE) # template: do not query attrs

        labels = buildfile.load_dependencies(
            "repository_root", artifact_def,
            labelm.Label(artifact_def.bazel_package), verbose=True)

        self.assertEqual(0, len(labels))

    def test_load_dependencies__artifact_def_deps(self):
        deps = ("//a/b/c:d",)
        artifact_def = buildpom.MavenArtifactDef("g1", "a2", "1.2.3", bazel_package="pack1", deps=deps)
        artifact_def = buildpom._augment_art_def_values(
            artifact_def, None, "pack1", "MVN-INF", None, None,
            genmode.TEMPLATE) # template: do not query attrs

        labels = buildfile.load_dependencies(
            "repository_root", artifact_def,
            labelm.Label(artifact_def.bazel_package), verbose=True)

        self.assertEqual(1, len(labels))
        self.assertEqual(labels[0].canonical_form, "//a/b/c:d")

    def test_load_dependencies__query_bazel(self):
        deps = ("//e/f/g:h",)
        artifact_def = buildpom.MavenArtifactDef("g1", "a2", "1.2.3", bazel_package="pack1", deps=deps)
        artifact_def = buildpom._augment_art_def_values(
            artifact_def, None, "pack1", "MVN-INF", None, None,
            genmode.DYNAMIC) # dynamic: query bazel for deps
        label = labelm.Label(artifact_def.bazel_package)

        with mock.patch("common.buildfile.bazel.query_dependencies") as query_deps_mock:
            query_deps_mock.return_value = [labelm.Label("//a/b/c:d")]

            labels = buildfile.load_dependencies(
                "repository_root", artifact_def, label, verbose=True)

        query_deps_mock.assert_called_once_with(
            "repository_root", artifact_def, label, True)
        self.assertEqual(2, len(labels))
        self.assertEqual(labels[0].canonical_form, "//e/f/g:h")
        self.assertEqual(labels[1].canonical_form, "//a/b/c:d")

    def test_filter_label(self):
        """
        Happy path.
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "dynamic", deps=[],
                           target_name="foo")
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/a1",
            generation_strategy=self.strat)
        label = labelm.Label("//lib/a1")

        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)

        self.assertIs(label, filtered_label)

    def test_filter_label__excluded_dependency_paths(self):
        """
        Verifies that globally defined excluded dependency paths are filtered
        out.
        """
        self.setup_collaborators(self._get_config(excluded_dependency_paths=["projects/protos/",]))
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/a1",
            generation_strategy=self.strat)
        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")

        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIs(label, filtered_label) # not filtered

        label = labelm.Label("//projects/protos/grail:java_protos")
        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIsNone(filtered_label) # filtered

    def test_filter_label__artifact_excluded_dependency_paths(self):
        """
        Verifies that locally defined excluded dependency paths are filtered
        out.
        """
        self.setup_collaborators(self._get_config())
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="projects/libs/pastry",
            excluded_dependency_paths=["src/abstractions",],
            generation_strategy=self.strat)

        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")
        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIs(label, filtered_label) # not filtered

        label = labelm.Label("//projects/libs/pastry/src/abstractions:foo")
        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIsNone(filtered_label) # filtered

    def test_filter_label__excluded_dependency_labels(self):
        """
        Verifies that excluded dependency labels are filtered out.
        """
        self.setup_collaborators(self._get_config(excluded_dependency_labels=["@maven//:ch_qos_logback_logback_classic",]))
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "dynamic", deps=[],
                           target_name="foo")
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/a1",
            generation_strategy=self.strat)

        label = labelm.Label("@maven//:ch_qos_logback_logback_classic")
        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIsNone(filtered_label) # filtered

        label = labelm.Label("//lib/a1")
        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)
        self.assertIs(filtered_label, label) # not filtered

        filtered_label = buildfile._filter_label(label,downstream_artifact_def,
                                                self.ws)

        self.assertIs(label, filtered_label)

    def test_src_dep_with_neverlink_enabled(self):
        """
        Verifies that no error is triggered when a dep has neverlink enabled
        and it has no BUILD.pom file.
        """
        self.setup_collaborators()
        self._write_basic_workspace_file(self.repo_root_path)
        self._write_library_root(self.repo_root_path, "lib")
        # no BUILD.pom file
        self._write_build_file(self.repo_root_path, "lib/lombok", neverlink=True)
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/a1",
            generation_strategy=self.strat)

        label = labelm.Label("//lib/lombok")

        filtered_label = buildfile._filter_label(label, downstream_artifact_def,
                                                self.ws)

        self.assertIsNone(filtered_label)

    def test_partition_and_filter_labels__source_label(self):
        """
        A source label that references an artifact-producing
        package is returned both as a source label (to keep crawling) and
        as a dependency.
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/a1", "dynamic", deps=[],
                           target_name="foo")
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/downstream",
            generation_strategy=self.strat)
        label = labelm.Label("//lib/a1")

        source_labels, deps = buildfile.partition_and_filter_labels(
            [label], downstream_artifact_def, self.ws)

        self.assertEqual([label], source_labels)
        self.assertEqual(1, len(deps))
        self.assertEqual("a1", deps[0].artifact_id)
        self.assertEqual("g1", deps[0].group_id)

    def test_partition_and_filter_labels__third_party_label(self):
        """
        A 3rd party label is not added to source_labels, but the associated
        dependency is still resolved and added to deps.
        """
        self.setup_collaborators()
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/downstream",
            generation_strategy=self.strat)
        label = labelm.Label("@maven//:guava")
        dep = dependencym.new_dep_from_maven_art_str(
            "com.google.guava:guava:20.0", "maven")
        self.strat._label_to_ext_dep = {label: dep}

        source_labels, deps = buildfile.partition_and_filter_labels(
            [label], downstream_artifact_def, self.ws)

        self.assertEqual([], source_labels)
        self.assertEqual([dep], deps)

    def test_partition_and_filter_labels__111_child_label(self):
        """
        A source label that references a 1:1:1 child package (which has
        no metadata of its own) is resolved by walking up to its 1:1:1
        parent. Since the downstream artifact is not part of the same
        1:1:1 group, the dependency is recorded against the parent
        artifact, not the child target that was referenced.

        Paths involved:
        - lib/src: the 1:1:1 parent, has metadata at lib/src/MVN-INF/BUILD.pom
        - lib/src/a1: the referenced 1:1:1 child package, has no metadata
          of its own, so it is resolved against its parent, lib/src
        - lib/downstream: the artifact that references //lib/src/a1,
          not part of the lib/src 1:1:1 group
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/src", "dynamic_111",
                           deps=[], target_name="foo")
        downstream_artifact_def = buildpom.MavenArtifactDef(
            "g", "a", "v",
            bazel_package="lib/downstream",
            generation_strategy=self.strat)
        label = labelm.Label("//lib/src/a1")

        source_labels, deps = buildfile.partition_and_filter_labels(
            [label], downstream_artifact_def, self.ws)

        self.assertEqual([label], source_labels)
        self.assertEqual(1, len(deps))
        self.assertEqual("src", deps[0].artifact_id)
        self.assertEqual("g1", deps[0].group_id)

    def test_partition_and_filter_labels__111_child_label_same_parent(self):
        """
        A source label that references a 1:1:1 child package is still
        added to source_labels (so it keeps getting crawled), but no
        dependency is recorded when the downstream artifact belongs to
        the same 1:1:1 group - all packages in the group collapse into a
        single emitted artifact, so there is no real dependency edge.

        Paths involved:
        - lib/src: the 1:1:1 parent, has metadata at lib/src/MVN-INF/BUILD.pom;
          also used here as the downstream artifact, since it is part of
          its own 1:1:1 group
        - lib/src/a1: the referenced 1:1:1 child package, has no metadata
          of its own, so it is resolved against its parent, lib/src
        """
        self.setup_collaborators()
        self._write_library_root(self.repo_root_path, "lib")
        self._add_artifact(self.repo_root_path, "lib/src", "dynamic_111",
                           deps=[], target_name="foo")
        downstream_artifact_def = self.ws.parse_maven_artifact_def("lib/src")
        label = labelm.Label("//lib/src/a1")

        source_labels, deps = buildfile.partition_and_filter_labels(
            [label], downstream_artifact_def, self.ws)

        self.assertEqual([label], source_labels)
        self.assertEqual([], deps)

    def setup_collaborators(self, cfg=None):
        """
        For tests that need a more bootstrapped system configured.
        """
        if cfg is None:
            cfg = self._get_config()
        self.repo_root_path = tempfile.mkdtemp("root")
        self.fac = generationstrategyfactory.GenerationStrategyFactory(
            self.repo_root_path, cfg, verbose=True)
        self.strat = self._get_strategy()
        self.ws = workspace.Workspace(self.repo_root_path, cfg, self.fac)

    def _get_strategy(self):
        strategy = pomgenerationstrategy.PomGenerationStrategy(
            "root", config.Config(), maveninstallinfo.NOOP,
            dependencymdm.DependencyMetadata(None),
            label_to_overridden_fq_label={}, verbose=True)
        strategy.initialize()
        return strategy

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)

    def _write_library_root(self, repo_root_path, package_rel_path):
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "LIBRARY.root"), "w") as f:
           f.write("foo")

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


if __name__ == '__main__':
    unittest.main()

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module manages Bazel workspace-level entities.
"""

from common import logger
from crawl import artifactprocessor
from crawl import bazel
from crawl import buildpom
from crawl import dependency


class Workspace:
    """
    Manages workspace-level entities and translates between Bazel and 
    Maven concepts.
    """
    def __init__(self, repo_root_path, config, maven_install_info,
                 pom_content, dependency_metadata, label_to_overridden_fq_label,
                 verbose=False):
        self.repo_root_path = repo_root_path
        self.excluded_dependency_paths = config.excluded_dependency_paths
        self.excluded_dependency_labels = config.excluded_dependency_labels
        self.source_exclusions = config.all_src_exclusions
        self.pom_content = pom_content
        self.verbose = verbose
        self.dependency_metadata = dependency_metadata
        self.change_detection_enabled = config.change_detection_enabled
        self.label_to_overridden_fq_label = label_to_overridden_fq_label
        self._label_to_ext_dep = self._parse_maven_install(
            maven_install_info, repo_root_path, label_to_overridden_fq_label)
        self._package_to_artifact_def = {} # cache for artifact_def instances

    @property
    def external_dependencies(self):
        """
        Returns an iterable of all external dependencies (dependency.Dependency
        instances), declared in this workspace.
        """
        return tuple(self._label_to_ext_dep.values())

    def parse_maven_artifact_def(self, package):
        """
        Parses the Maven metadata files files in the specified package and 
        returns a MavenArtifactDef instance.

        Returns None if there is no BUILD.pom file at the specified path.
        """
        if package in self._package_to_artifact_def:
            return self._package_to_artifact_def[package]
        art_def = buildpom.parse_maven_artifact_def(self.repo_root_path, package)
        if art_def is not None:
            art_def = artifactprocessor.augment_artifact_def(
                self.repo_root_path, art_def, self.source_exclusions,
                self.change_detection_enabled)
        # cache result, next time it is returned from cache
        self._package_to_artifact_def[package] = art_def
        return art_def

    def parse_dep_labels(self, dep_labels):
        """
        Given a list of Bazel labels, returns a list of Dependency instances.
     
        Example input:
            ["@maven//:com_google_guava_guava//jar",
             "@maven//:com_github_ben_manes_caffeine_caffeine//jar",
             "//projects/libs/servicelibs/srpc/srpc-api:srpc-api"]

        See dependency.Dependency
        """
        deps = []
        for label in dep_labels:
            dep = self._parse_dep_label(label)
            if dep is not None:
                deps.append(dep)
        return deps

    def normalize_deps(self, artifact_def, deps):
        """
        Normalizes the specified deps, in the context of the specified 
        owning artifact_def.

        This method performs the following steps:

          - removes deps that point back to the artifact that references them

        Specifically, this method handles the case where, in the BUILD file, 
        a java_library has a dependency on a (private) target defined in the 
        same Bazel Package. This configuration is generally not supported,
        except when the referenced targets are gRPC related.
        """
        updated_deps = []
        for dep in deps:
            if dep.bazel_package is not None and dep.bazel_package == artifact_def.bazel_package:
                # this dep has the same bazel_package as the artifact 
                # referencing the dep, skip it, unless this bazel package
                # actually does not produce artifacts
                if artifact_def.pom_generation_mode.produces_artifact:
                    continue
            updated_deps.append(dep)
        return updated_deps

    def filter_artifact_producing_packages(self, packages):
        """
        Given a list of packages, returns those that are actually producing
        a Maven artifact. 

        This is based on the pom_generation_mode specified in the BUILD.pom 
        file.
        """
        art_defs = [self.parse_maven_artifact_def(p) for p in packages]
        return [art_def.bazel_package for art_def in art_defs if art_def.pom_generation_mode.produces_artifact]

    def _parse_dep_label(self, dep_label):
        if dep_label in self.excluded_dependency_labels:
            return None

        if dep_label.startswith("@"):
            if dep_label not in self._label_to_ext_dep:
                print(self._label_to_ext_dep.values())
                raise Exception("Unknown external dependency - please make sure all maven install json files have been registered with pomgen (by setting maven_install_paths in the pomgen config file): [%s]" % dep_label)
            return self._label_to_ext_dep[dep_label]
        elif dep_label.startswith("//"):
            # monorepo src ref:
            package_path = dep_label[2:] # remove leading "//"
            target_name = None
            i = package_path.rfind(":")
            if i != -1:
                target_name = package_path[i+1:]
                package_path = package_path[:i]

            for excluded_dependency_path in self.excluded_dependency_paths:
                if package_path.startswith(excluded_dependency_path):
                    return None

            maven_artifact_def = self.parse_maven_artifact_def(package_path)
            if maven_artifact_def is None:
                if bazel.is_never_link_dep(self.repo_root_path, dep_label):
                    return None

                raise Exception("no BUILD.pom file in package [%s]" % package_path)
            else:
                return dependency.new_dep_from_maven_artifact_def(maven_artifact_def, target_name)
        else:
            raise Exception("bad label [%s]" % dep_label)

    def _parse_maven_install(self, maven_install_info, repo_root_path, 
                             label_to_overridden_fq_label):
        """
        Parses all pinned json files for the specified maven_install rules.
        """
        names_and_paths = maven_install_info.get_maven_install_names_and_paths(
            repo_root_path)

        dep_to_transitives = bazel.parse_maven_install(
            names_and_paths, label_to_overridden_fq_label)

        label_to_dep = {}
        for dep, transitives in dep_to_transitives:
            label = dep.bazel_label_name
            label_to_dep[label] = dep
            if self.verbose:
                logger.debug("Registered dep %s" % label)
            self.dependency_metadata.register_transitives(dep, transitives)

        return label_to_dep

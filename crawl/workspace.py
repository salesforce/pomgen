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
    Manages workspace-level information and translates between Bazel and 
    Maven concepts.
    """
    def __init__(self, repo_root_path, config, maven_install_info,
                 pom_content, dependency_metadata, override_file_info = [], verbose=False):
        self.repo_root_path = repo_root_path
        self.excluded_dependency_paths = config.excluded_dependency_paths
        self.excluded_dependency_labels = config.excluded_dependency_labels
        self.source_exclusions = config.all_src_exclusions
        self.pom_content = pom_content
        self.verbose = verbose
        self.dependency_metadata = dependency_metadata
        self.change_detection_enabled = config.change_detection_enabled
        self.override_file_info = override_file_info
        self._name_to_ext_deps = self._parse_maven_install(maven_install_info, repo_root_path)
        self._package_to_artifact_def = {} # cache for artifact_def instances


    @property
    def name_to_external_dependencies(self):
        """
        Returns a dict for all external dependencies declared for this 
        WORKSPACE.
 
        The mapping is of the form: {maven_jar.name: Dependency instance}.
        """
        return self._name_to_ext_deps

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
            if dep_label not in self._name_to_ext_deps:
                print(self._name_to_ext_deps.values())
                raise Exception("Unknown external dependency - please make sure all maven install json files have been registered with pomgen (by setting maven_install_paths in the pomgen config file): [%s]" % dep_label)
            return self._name_to_ext_deps[dep_label]
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

    def _parse_maven_install(self, maven_install_info, repo_root_path):
        """
        Parses all pinned json files for the specified maven_install rules.

        Returns a dictionary mapping of the dependency label (as used in BUILD
        files) -> the corresponding dependency.Dependency instance.
        """
        result = {}
        transitives_list = []
        for name_and_path in maven_install_info.get_maven_install_names_and_paths(repo_root_path):
            mvn_install_name, json_file_path = name_and_path
            parse_result = bazel.parse_maven_install(mvn_install_name, json_file_path)
            for dep, transitives, exclusions in parse_result:
                key = dep.bazel_label_name
                if self.verbose:
                    logger.debug("Registered dep %s" % key)
                result[key] = dep
                transitives_list.append({dep : transitives})
                self.dependency_metadata.register_exclusions(dep, exclusions)

        # Overrides the deps honoring the override file
        for key, dep in result.items():
            if self.override_file_info == []:
                break
            overridden_dep = self.override_file_info.overridden_dep_value(dep)
            if overridden_dep in result.keys():
                result[key] = result[overridden_dep]

        # Registers the overridden transitives
        for t in transitives_list:
            for dep, transitives in t.items():
                if not self.override_file_info == []:
                    transitives = self.override_file_info.override_deps(transitives, result)
                self.dependency_metadata.register_transitives(dep, transitives)

        return result
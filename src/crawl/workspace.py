"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module manages Bazel workspace-level entities.

TODO - this module has been gutted in 2025 as a result of a major refactor,
it would be good to find a better home for the remaining pieces here.
"""


from crawl import artifactprocessor
from crawl import buildpom


class Workspace:
    """
    Manages workspace-level entities and translates between Bazel and 
    Maven concepts.
    """
    def __init__(self, repo_root_path, config, generation_strategy_factory):
        self.repo_root_path = repo_root_path
        self.source_exclusions = config.all_src_exclusions
        self.change_detection_enabled = config.change_detection_enabled
        self.excluded_dependency_paths = config.excluded_dependency_paths
        self.excluded_dependency_labels = config.excluded_dependency_labels
        self.generation_strategy_factory = generation_strategy_factory
        self._package_to_artifact_def = {} # cache for artifact_def instances

    def parse_maven_artifact_def(self, package):
        """
        Parses the Maven metadata files files at the specified (bazel) package,
        which is a relative path from the repository root.

        Returns a MavenArtifactDef instance, None if there is no BUILD.pom
        file at the specified path.
        """
        if package in self._package_to_artifact_def:
            return self._package_to_artifact_def[package]
        strategy = self.generation_strategy_factory.get_strategy_for_package(package)
        if strategy is None:
            return None
        else:
            art_def = buildpom.parse_maven_artifact_def(self.repo_root_path, package, strategy)
            assert art_def is not None
            art_def = artifactprocessor.augment_artifact_def(
                self.repo_root_path, art_def, self.source_exclusions,
                self.change_detection_enabled)
            # cache result, next time it is returned from cache
            self._package_to_artifact_def[package] = art_def
            return art_def

    def filter_artifact_producing_packages(self, packages):
        """
        Given a list of packages, returns those that are actually producing
        a Maven artifact. 

        This is based on the pom_generation_mode specified in the BUILD.pom 
        file.
        """
        art_defs = [self.parse_maven_artifact_def(p) for p in packages]
        return [art_def.bazel_package for art_def in art_defs if art_def.pom_generation_mode.produces_artifact]

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module manages Bazel workspace-level entities.

TODO - this module has been gutted in 2025 as a result of a major refactor,
it would be good to find a better home for the remaining pieces here.
"""


import common.genmode as genmode
import crawl.artifactprocessor as artifactprocessor
import crawl.buildpom as buildpom
import os.path


class Workspace:
    """
    Manages workspace-level entities and translates between Bazel and 
    Maven concepts.
    """
    def __init__(self, repo_root_path, config, generation_strategy_factory, cache_artifact_defs=True):
        self.repo_root_path = repo_root_path
        self.source_exclusions = config.all_src_exclusions
        self.change_detection_enabled = config.change_detection_enabled
        self.excluded_dependency_paths = config.excluded_dependency_paths
        self.excluded_dependency_labels = config.excluded_dependency_labels
        self.generation_strategy_factory = generation_strategy_factory
        self.cache_artifact_defs = cache_artifact_defs
        self._package_to_artifact_def = {} # cache for artifact_def instances

    def parse_maven_artifact_def(self, package, downstream_artifact_def=None):
        """
        Parses the Maven metadata files files at the specified (bazel) package,
        which is a relative path from the repository root.

        The given downstream_artifact_def is the artifact def that references
        (drags in) this package.

        Returns a MavenArtifactDef instance, None if there is no metadata
        directory at the specified package.
        """
        assert isinstance(package, str)
        if package in self._package_to_artifact_def:
            return self._package_to_artifact_def[package]
        strategy = self.generation_strategy_factory.get_strategy_for_package(package)
        if strategy is None:
            # this directory doesn't have any metadata - we default
            # to 111 subpackage if this is a 1:1:1 enabled project structure
            # TODO review how how this works with neverlink
            parent_package, strat = self._get_parent_package_of(package)
            if parent_package is None:
                # 111 mode potentially, check is in crawler, should move here?
                return None
            assert parent_package is not None, "metadata does not exist at [%s], nor at any parent directory" % package
            if parent_package in self._package_to_artifact_def:
                parent_art_def = self._package_to_artifact_def[parent_package]
            else:
                assert strat is not None, "strategy cannot be None - this is a bug"
                parent_art_def = self._parse_artifact_def(parent_package, strat)
                if self.cache_artifact_defs:
                    self._package_to_artifact_def[parent_package] = parent_art_def
            assert parent_art_def is not None
            assert parent_art_def.generation_mode is genmode.DYNAMIC_ONEONEONE, "did not find any metadata at [%s], found parent metadata at [%s], however parent does not have required 1:1:1 mode enabled" % (package, parent_package)
            art_def = _build_oneoneone_child_artifact_def(package, parent_art_def)
        else:
            art_def = self._parse_artifact_def(package, strategy)

        if self.cache_artifact_defs:
            self._package_to_artifact_def[package] = art_def
        return art_def

    def filter_artifact_producing_packages(self, packages):
        """
        Given a list of packages, returns those that are actually producing
        a Maven artifact. 

        This is based on the generation_mode specified in the metadata
        (for ex BUILD.pom file).
        """
        art_defs = [self.parse_maven_artifact_def(p) for p in packages]
        return [art_def.bazel_package for art_def in art_defs if art_def.generation_mode.produces_artifact]

    def _get_parent_package_of(self, package):
        """
        Finds the closest parent metadata directory by walking up the directory
        tree, starting at the specified package.

        Returns a tuple of:
          - (None, None) if no parent metadata directory exists
          - (package path, generation strategy instance) if parent md exists
        """
        emergency_break = 0
        while True:
            strat = self.generation_strategy_factory.get_strategy_for_package(package)
            if strat is None:
                package = os.path.dirname(package)
                if len(package) == 0:
                    return None, None
                else:
                    assert emergency_break < 50 # just in case
                    emergency_break += 1
            else:
                return package, strat

    def _parse_artifact_def(self, package, strategy):
        art_def = buildpom.parse_maven_artifact_def(self.repo_root_path, package, strategy)
        if art_def is not None:
            art_def = artifactprocessor.augment_artifact_def(
                self.repo_root_path, art_def, self.source_exclusions,
                self.change_detection_enabled)
        return art_def


def _build_oneoneone_child_artifact_def(package, parent_artifact_def):
    return buildpom.MavenArtifactDef(
        parent_artifact_def=parent_artifact_def,
        generation_mode=genmode.ONEONEONE_CHILD,
        bazel_package=package,
        bazel_target=os.path.basename(package),
        generation_strategy=parent_artifact_def.generation_strategy,
        library_path=parent_artifact_def.library_path,
        requires_release=False,
        group_id = None,
        artifact_id = None,
        version = parent_artifact_def.version,
    )

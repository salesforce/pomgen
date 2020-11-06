"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module manages Bazel workspace-level entities.
"""

from crawl import artifactprocessor
from crawl import buildpom
from crawl import dependency
from crawl import bazel

class Workspace:
    """
    Manages workspace-level information and translates between Bazel and 
    Maven concepts.
    """

    def __init__(self, repo_root_path, excluded_dependency_paths, 
                 source_exclusions, 
                 maven_install_rule_names,
                 pom_content):
        self.repo_root_path = repo_root_path
        self.excluded_dependency_paths = excluded_dependency_paths
        self.source_exclusions = source_exclusions
        self.pom_content = pom_content
        self._name_to_ext_deps = self._parse_maven_install(maven_install_rule_names)
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
            art_def = artifactprocessor.augment_artifact_def(self.repo_root_path, art_def, self.source_exclusions)
        # cache result, next time it is returned from cache
        self._package_to_artifact_def[package] = art_def
        return art_def

    def parse_dep_labels(self, dep_labels):
        """
        Given a list of Bazel labels, returns a list of Dependency instances.
     
        Example input:

            ["@com_google_guava_guava//jar",
             "@com_github_ben_manes_caffeine_caffeine//jar",
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
        if dep_label.startswith("@"):
            # external maven jar:
            ext_dep_name = dep_label[1:].strip()
            dep_split = ext_dep_name.split(':')
            if len(dep_split) == 1:
                return self._name_to_ext_deps.get(ext_dep_name, None)
            else:
                return self._name_to_ext_deps.get(dep_split[1], None)
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
                raise Exception("no BUILD.pom file in package [%s]" % package_path)
            else:
                return dependency.new_dep_from_maven_artifact_def(maven_artifact_def, target_name)
        else:
            raise Exception("bad label [%s]" % dep_label)

    def _parse_maven_install(self, rule_names):
        """
        Parse the dependencies inside each maven_install in rule_names.
        There should be a ${rule}_install.json file at the root of the
        repository for each rule.

        rule_names are processed in reverse order so that the first one wins.
        This is to handle the legacy naming case. The full name used my
        maven_install should be used in future versions. This is accomodate
        repositories to be able to migrate to maven_install dependency names.

        Returns a dictionary mapping the value of the coord santized for Bazel
        to a Dependency instance. It also has keys for the fully qualified
        maven_install rule.
        """
        result = {}
        for each_rule in rule_names[::-1]:
            for name, coord in bazel.query_maven_install(self.repo_root_path, each_rule).items():
                fully_qualified_name = '@%s//:%s' % (each_rule, name)
                dep = dependency.new_dep_from_maven_art_str(coord, fully_qualified_name)
                if dep.classifier != 'sources':
                    result[fully_qualified_name] = dep
                    # This should be factored out eventually and use fully
                    # qualified name once maven_jar names are removed
                    # completely, so should this
                    result[name] = dependency.new_dep_from_maven_art_str(coord, name)
        return result

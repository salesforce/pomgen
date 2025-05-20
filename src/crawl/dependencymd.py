"""
Copyright (c) 2020, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

class DependencyMetadata:
    """
    This class provides metadata about dependencies. This is data that cannot
    be discovered by crawling Bazel BUILD files.
    """
    def __init__(self, jar_artifact_classifier):
        self._dep_to_transitives = {}
        self._dep_to_exclusions = {}
        self._dep_key_to_dependency = {}
        self._jar_artifact_classifier = jar_artifact_classifier

    def get_transitive_closure(self, dependency):
        """
        Returns the transitive closure of dependencies that the specified
        dependency has, as a list of dependency.Dependency instances.

        This method is a noop for dependency instances that do not represent
        external (from Maven Central/Nexus) Maven dependencies.
        """
        key = self._get_key(dependency)
        return self._dep_to_transitives.get(key, [])

    def get_classifier(self, dependency):
        if dependency.classifier is not None:
            return dependency.classifier
        else:
            if dependency.bazel_buildable:
                return self._jar_artifact_classifier
        return None
                
    def register_transitives(self, dependency, transitives):
        key = self._get_key(dependency)
        assert key is not None, "no key for dependency: [%s]" % dependency
        assert key not in self._dep_to_transitives, "duplicate key [%s] for dependency [%s]" % (key, dependency)
        self._dep_to_transitives[key] = transitives
        self._dep_key_to_dependency[key] = dependency

    def clear(self):
        self._dep_to_transitives.clear()
        self._dep_to_exclusions.clear()
        self._dep_key_to_dependency.clear()

    def _get_key(self, dependency):
        return dependency.bazel_label_name # the label used in BUILD files

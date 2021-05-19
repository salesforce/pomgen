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
    def __init__(self):
        self._dep_to_transitives = {}
        self._dep_to_exclusions = {}

    def get_transitive_closure(self, dependency):
        """
        Returns a list of dependency.Dependency instances, the transitive
        closure of dependencies the specified dependency references.

        This method is a noop for dependency instances that do not represent
        external (from Maven Central/Nexus) Maven dependencies.
        """
        key = self._get_key(dependency)
        return self._dep_to_transitives.get(key, [])

    def get_transitive_exclusions(self, dependency):
        """
        Returns a list of dependency.Dependency instances that represent the
        exclusions for the specified dependency.

        These are the exclusions in the Maven/pom.xml sense - these dependencies
        are excluded from the transitive closure of depdendencies.

        This method is a noop for dependency instances that do not represent
        external (from Maven Central/Nexus) Maven dependencies.
        """
        key = self._get_key(dependency)
        return self._dep_to_exclusions.get(key, [])

    def register_transitives(self, dependency, transitives):
        key = self._get_key(dependency)
        assert key is not None, "no key for dependency: [%s]" % dependency
        assert not key in self._dep_to_transitives, "duplicate key [%s] for dependency [%]" % (key, dependency)
        self._dep_to_transitives[key] = transitives

    def register_exclusions(self, dependency, exclusions):
        key = self._get_key(dependency)
        assert key is not None, "no key for dependency: [%s]" % dependency
        assert not key in self._dep_to_exclusions, "duplicate key [%s] for dependency [%s]" % (key, dependency)
        self._dep_to_exclusions[key] = exclusions

    def _get_key(self, dependency):
        return dependency.bazel_label_name # the label used in BUILD files

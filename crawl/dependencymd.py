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
        return self._dep_to_transitives.get(dependency, [])

    def get_transitive_exclusions(self, dependency):
        """
        Returns a list of dependency.Dependency instances that represent the
        exclusions for the specified dependency.

        These are the exclusions in the Maven/pom.xml sense - these dependencies
        are excluded from the transitive closure of depdendencies.

        This method is a noop for dependency instances that do not represent
        external (from Maven Central/Nexus) Maven dependencies.
        """
        return self._dep_to_exclusions.get(dependency, [])

    def register_transitives(self, dependency, transitives):
        assert not dependency in self._dep_to_transitives, "duplicate key [%s]" % dependency
        self._dep_to_transitives[dependency] = transitives

    def register_exclusions(self, dependency, exclusions):
        assert not dependency in self._dep_to_exclusions, "duplicate key [%s]" % dependency
        self._dep_to_exclusions[dependency] = exclusions

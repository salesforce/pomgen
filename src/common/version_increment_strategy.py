"""
Copyright (c) 2023, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
from datetime import datetime, timezone


# valid version increment strategies are:
VERSION_INCREMENT_STRATEGIES = ("major", "minor", "patch", "calver",)

SNAPSHOT_QUAL = "-SNAPSHOT"


def get_rel_qualifier_increment_strategy(last_released_version):
    """
    See /docs/ci.md#using-a-different-version-increment-mode-for-transitives.
    """
    return RelQualifierIncrementStrategy(last_released_version)


def get_version_increment_strategy(strategy_name):
    assert strategy_name in VERSION_INCREMENT_STRATEGIES, "Unknown version increment strategy [%s], valid strategies are %s" % (strategy_name, VERSION_INCREMENT_STRATEGIES)

    if strategy_name == "major":
        return MajorVersionIncrementStrategy()
    elif strategy_name == "minor":
        return MinorVersionIncrementStrategy()
    elif strategy_name == "patch":
        return PatchVersionIncrementStrategy()
    elif strategy_name == "calver":
        return CalverVersionIncrementStrategy()
    else:
        raise Exception("Bug! Bad version increment strategy: %s" % strategy_name)


class VersionIncrementStrategy:
    """
    Encapsulates next version computations.
    """
    def get_next_release_version(self, current_version):
        """
        Given a current_version, returns the version to use for the next
        release.

        For example: 1.0.0-SNAPSHOT -> 1.0.0
        """
        raise AssertionError("Implement me")

    def get_next_development_version(self, current_version):
        """
        Given a current_version, returns the version to use as the next
        in-development version.

        For example: 1.0.0 -> 2.0.0-SNAPSHOT
        """
        raise AssertionError("Implement me")


class DefaultVersionIncrementStrategy:

    def get_next_release_version(self, current_version):
        """
        This default implementation just removes the "-SNAPSHOT" qualifier, if
        the specified current_version has that qualifier.

        For example: 1.0.0-SNAPSHOT -> 1.0.0
        """
        if current_version.endswith(SNAPSHOT_QUAL):
            return current_version[0:-len(SNAPSHOT_QUAL)]
        else:
            return current_version

    def get_next_development_version(self, current_version):
        """
        This default implementation increments the version and adds the
        "-SNAPSHOT" qualifier, if the specified current_version does not have it
        yet.

        For example: 1.0.0 -> 2.0.0-SNAPSHOT
        """
        qualifier, version = _get_qualifier_and_version(current_version)
        next_version = self.get_next_version__hook(version)
        if qualifier is not None:
            next_version += qualifier
        if not next_version.endswith(SNAPSHOT_QUAL):
            next_version += SNAPSHOT_QUAL
        return next_version

    def get_next_version_hook(self, current_version):
        """
        Given a current version, returns the next logic version.

        For example: 1.0.0 -> 2.0.0.

        Meant to be implemented in subclasses.
        """
        raise AssertionError("subclasses must implement")


class MajorVersionIncrementStrategy(DefaultVersionIncrementStrategy):

    def get_next_version__hook(self, current_version):
        """
        Increments the major component of a semver version.

        For example:

        1.0.0 -> 2.0.0
        1.1.1 -> 2.0.0
        1.0.9 -> 2.0.0
        1.1   -> 2.0.0
        1     -> 2.0.0
        """
        components = current_version.split(".")
        major_component = int(components[0])
        return "%i.0.0" % (major_component + 1)


class MinorVersionIncrementStrategy(DefaultVersionIncrementStrategy):

    def get_next_version__hook(self, current_version):
        """
        Increments the minor component of a semver version.

        For example:

        1.0.0 -> 1.1.0
        1.1.1 -> 1.2.0
        1.1   -> 1.2.0
        1     -> 1.1.0
        """
        components = current_version.split(".")
        if len(components) > 1:
            minor_component = int(components[1])
        else:
            minor_component = 0
        return "%s.%i.0" % (components[0], minor_component + 1)


class PatchVersionIncrementStrategy(DefaultVersionIncrementStrategy):

    def get_next_version__hook(self, current_version):
        """
        Increments the patch component of a semver version.

        For example:

        1.0.0 -> 1.0.1
        1.1.1 -> 1.1.2
        1.2   -> 1.2.1
        1     -> 1.0.1
        """
        components = current_version.split(".")
        if len(components) > 2:
            minor_component = components[1]
            patch_component = int(components[2])
        elif len(components) == 2:
            minor_component = components[1]
            patch_component = 0
        else:
            minor_component = 0
            patch_component = 0
        return "%s.%s.%i" % (components[0], minor_component, patch_component + 1)


class CalverVersionIncrementStrategy(DefaultVersionIncrementStrategy):

    def get_next_release_version(self, current_version):
        """
        The next release version for Calver re-computes the version instead of
        only removing the -SNAPSHOT qualifier, because we want to use the
        current date in the version string (the date when the release
        actually happened).

        For simplicity sake, we just get next dev version (which already
        recomputes the version) and remove the -SNAPSHOT qualifier.
        """
        release_version = self.get_next_development_version(current_version)
        i = release_version.index(SNAPSHOT_QUAL)
        return release_version[0:i]

    def get_next_version__hook(self, current_version):
        """
        Given a current version of `20230605.1`, produces <todaydate>.1
        (or <todaydate>.2 if the current version is already <todaydate>.1).
        """
        components = current_version.split(".")
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        if today != components[0]:
            return "%s.1" % today
        else:
            daily_version = int(components[1])
            return "%s.%i" % (today, daily_version + 1)


class RelQualifierIncrementStrategy(VersionIncrementStrategy):

    OLD_REL_QUALIFIER_PREFIX = "-rel-"
    REL_QUALIFIER_PREFIX = "-rel"

    def __init__(self, last_released_version):
        self.last_released_version = "0.0.0" if last_released_version is None else last_released_version

    def get_next_release_version(self, current_version):
        """
        Takes the current "last_released_version" and increments the "-rel"
        qualifier. If the "-rel" qualifier is not there, it is added.
        """
        return RelQualifierIncrementStrategy._incr_rel_qualifier(self.last_released_version)

    def get_next_development_version(self, current_version):
        """
        Just returns the current version.
        """
        if not current_version.endswith(SNAPSHOT_QUAL):
            current_version += SNAPSHOT_QUAL
        return current_version

    @classmethod
    def _incr_rel_qualifier(clazz, version):
        start_rel_qual_i = None
        end_rel_qual_i = None
        current_counter_value = None
        for qual in (RelQualifierIncrementStrategy.OLD_REL_QUALIFIER_PREFIX,
                     RelQualifierIncrementStrategy.REL_QUALIFIER_PREFIX):
            start_rel_qual_i = version.rfind(qual)
            if start_rel_qual_i == -1:
                continue
            start_counter_i = start_rel_qual_i + len(qual)
            end_rel_qual_i = version.find("-", start_counter_i + 1)
            if end_rel_qual_i == -1:
                end_rel_qual_i = len(version)
            counter_str = version[start_counter_i:end_rel_qual_i]
            current_counter_value = int(counter_str)
            break

        if current_counter_value is None:
            start_rel_qual_i = end_rel_qual_i = len(version)
            current_counter_value = 0
        return "%s%s%s%s" % (version[:start_rel_qual_i],
                             RelQualifierIncrementStrategy.REL_QUALIFIER_PREFIX,
                             current_counter_value + 1,
                             version[end_rel_qual_i:])


def _get_qualifier_and_version(version):
    """
    Splits the version qualifier from the version and returns a tuple:
    (qualifier, version)

    If the specified version doesn't have a qualifier, returns
    (None, version)
    """
    i = version.find('-')
    version_has_qualifier = i != -1
    version_qualifier = None
    if version_has_qualifier:
        version_qualifier = version[i:]
        version = version[0:-len(version_qualifier)]
    return version_qualifier, version

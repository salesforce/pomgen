"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


version related shared code.
"""

from . import code
from collections import namedtuple
import re


version_re = re.compile("(^.*version *= *[\"'])(.*?)([\"'].*)$", re.S)


def get_version_increment_strategy(build_pom_content, path):
    """
    Returns a version increment strategy instance based on the value of
    maven_artifact_update.version_increment_strategy in the specified
    BUILD.pom content.
   
    The version increment strategy is a function that takes a single (version)
    string as argument, and that returns another string, the next version.

    Examples:
        "1.0.0" -> "2.0.0"
        "1.0.2" -> "1.1.2"
        "1.0.2" -> "1.0.3"
        "1.0.0-SNAPSHOT" -> "2.0.0-SNAPSHOT"
        "1.0.0-scone_70x" -> "2.0.0-scone_70x"
        "1.0.0-scone_70x-SNAPSHOT" -> "2.0.0-scone_70x-SNAPSHOT"
    """
    maven_art_up = _parse_maven_artifact_update(build_pom_content, path)
    if maven_art_up.version_increment_strategy == "major":
        incr_strat = _get_major_version_increment_strategy()
    elif maven_art_up.version_increment_strategy == "minor":
        incr_strat = _get_minor_version_increment_strategy()
    elif maven_art_up.version_increment_strategy == "patch":
        incr_strat = _get_patch_version_increment_strategy()
    else:
        raise Exception("Unknown version increment strategy: %s" % maven_art_up.version_increment_strategy)
    return lambda version: version_update_handler(version, incr_strat)


def parse_build_pom_version(build_pom_content):
    """
    Returns the value of maven_artifact.version.
    """
    m = version_re.search(build_pom_content)
    if m is None:
        # possible if pom_generation_mode=skip
        return None
    else:
        return m.group(2).strip()


def parse_build_pom_released_version(build_pom_released_content):
    """
    Returns the value of released_maven_artifact.version.
    """
    return parse_build_pom_version(build_pom_released_content)


def get_release_version(current_version, last_released_version=None, incremental_release=False):
    """
    If incremental_release is False:
        If current_version ends with "-SNAPSHOT", removes that, otherwise
        returns current_version without modifications.

    If incremental_release is True:
        Adds or increments the "rel" qualifier to the last_released_version.
        If last_released_version is None it is defaulted to 0.0.0.
    """
    if incremental_release:
        if last_released_version is None:
            last_released_version = "0.0.0"
        return _incr_rel_qualifier(last_released_version)
    else:
        if current_version is None:
            return None
        elif current_version.endswith("-SNAPSHOT"):
            return current_version[0:-len("-SNAPSHOT")]
        else:
            return current_version


def get_next_dev_version(current_version, version_increment_strategy, incremental_release=False):
    """
    Returns the next development version to use. The development version
    always ends with "-SNAPSHOT".

    If incremental_release is False:
        Increments and returns current_version using the specified
        version_increment_strategy.

    If incremental_release is True:
        Returns the current version (because it hasn't been released yet)
    """
    if current_version is None:
        return None
    if incremental_release:
        next_version = current_version
    else:
        next_version = version_increment_strategy(current_version)
    if not next_version.endswith("-SNAPSHOT"):
        next_version += "-SNAPSHOT"
    return next_version


# only used internally for parsing
MavenArtifactUpdate = namedtuple("MavenArtifactUpdate", "version_increment_strategy")

def maven_artifact_update(version_increment_strategy):    
    """
    This function is only intended to be called from BUILD.pom files.
    """
    return MavenArtifactUpdate(version_increment_strategy)


def version_update_handler(version, version_update_strategy):
    """
    This method takes the current version and a function that produces a new
    version, and removes and re-adds non-numeric version qualifiers (such 
    as "-SNAPSHOT"), if necessary.

    1st argument: the current version
    2nd argument: a function that takes a single argument, the current numeric
                  version without version qualifier suffix, and that computes 
                  the next version.

    Note that the version qualifier MUST start with a '-'.
    """
    i = version.find('-')
    version_has_qualifier = i != -1
    version_qualifier = version[i:] if version_has_qualifier else ""
    if version_has_qualifier:
        version = version[0:-len(version_qualifier)]
    next_version = version_update_strategy(version)
    if version_has_qualifier:
        next_version += version_qualifier
    return next_version


OLD_REL_QUALIFIER_PREFIX = "-rel-"
REL_QUALIFIER_PREFIX = "-rel"


def _incr_rel_qualifier(version):
    start_rel_qual_i = None
    end_rel_qual_i = None
    current_counter_value = None
    for qual in (OLD_REL_QUALIFIER_PREFIX, REL_QUALIFIER_PREFIX,):
        start_rel_qual_i = version.rfind(qual)
        if start_rel_qual_i == -1:
            continue
        start_counter_i = start_rel_qual_i + len(qual)
        end_rel_qual_i = version.rfind("-", start_counter_i + 1)
        if end_rel_qual_i == -1:
            end_rel_qual_i = len(version)
        counter_str = version[start_counter_i:end_rel_qual_i]
        current_counter_value = int(counter_str)
        break

    if current_counter_value is None:
        start_rel_qual_i = end_rel_qual_i = len(version)
        current_counter_value = 0
    return "%s%s%s%s" % (version[:start_rel_qual_i],
                         REL_QUALIFIER_PREFIX,
                         current_counter_value + 1,
                         version[end_rel_qual_i:])


def _parse_maven_artifact_update(build_pom_content, path):
    maven_art_up_func = code.get_function_block(build_pom_content,
                                                "maven_artifact_update")
    try:
        return eval(maven_art_up_func)
    except:
        print("[ERROR] Cannot parse [%s]: %s" % (path, sys.exc_info()))
        raise


def _get_major_version_increment_strategy():
    def increment_major(version):
        i = version.index(".")
        major_version = int(version[0:i])
        return "%i.0.0" % (major_version + 1)
    return increment_major


def _get_minor_version_increment_strategy():
    def increment_minor(version):
        pieces = version.split(".")
        minor_version = int(pieces[1])
        return "%s.%i.0" % (pieces[0], minor_version + 1)
    return increment_minor


def _get_patch_version_increment_strategy():
    def increment_patch(version):
        pieces = version.split(".")
        patch_version = int(pieces[2])
        return "%s.%s.%i" % (pieces[0], pieces[1], patch_version + 1)
    return increment_patch

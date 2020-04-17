"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is responsible for updating BUILD.pom and BUILD.pom.released files.
"""
from common import mdfiles
from common import pomgenmode
from common import version
from crawl import git
import os
import re
import sys

def update_build_pom_file(root_path, 
                          packages,
                          new_version=None,
                          update_version_using_version_incr_strat=False,
                          new_version_incr_strat=None,
                          set_version_to_last_released_version=False,
                          version_qualifier_to_add=None,
                          new_pom_generation_mode=None,
                          add_pom_generation_mode_if_missing=False):
    """
    If a non-None value is provided, updates the following values in BUILD.pom 
    files in the specified packages:
        - version (also version qualifier)
        - version_increment_strategy
        - pom_generation_mode
        - pom_generation_mode
    """
    for package in packages:
        build_pom_content, build_pom_path = mdfiles.read_file(root_path, package, mdfiles.BUILD_POM_FILE_NAME)
        if build_pom_content is None:
            raise Exception("Invalid package [%s]" % package)
        try:
            current_version = version.parse_build_pom_version(build_pom_content)
            updated_version = new_version

            # increment current version using version increment strategy
            if updated_version is None and update_version_using_version_incr_strat:
                vers_incr_strat = version.get_version_increment_strategy(build_pom_content, build_pom_path)
                updated_version = vers_incr_strat(current_version)

            # set version back to previously released version
            if updated_version is None and set_version_to_last_released_version:
                build_pom_released_content, _ = mdfiles.read_file(root_path, package, "BUILD.pom.released")
                if build_pom_released_content is None:
                    # if the BUILD.pom.released file cannot be read (because it
                    # doesn't exist (yet), this is a noop - we don't want to 
                    # fail here because typical usage is to update many 
                    # artifacts at once
                    pass
                else:
                    updated_version = version.parse_build_pom_released_version(build_pom_released_content)

            # add version qualifier to current version
            if updated_version is None and version_qualifier_to_add is not None:
                update_strategy = _get_version_qualifier_update_strategy(version_qualifier_to_add)
                updated_version = version.version_update_handler(current_version, update_strategy)

            if updated_version is not None:
                build_pom_content = _update_version_in_build_pom_content(build_pom_content, updated_version)
            if new_version_incr_strat is not None:
                build_pom_content = _update_version_incr_strategy_in_build_pom_content(build_pom_content, new_version_incr_strat)
            if new_pom_generation_mode is not None:
                build_pom_content = _update_pom_generation_mode_in_build_pom_content(build_pom_content, new_pom_generation_mode)
            if add_pom_generation_mode_if_missing:
                build_pom_content = _add_pom_generation_mode_if_missing_in_build_pom_content(build_pom_content)
                    
            mdfiles.write_file(build_pom_content, root_path, package, mdfiles.BUILD_POM_FILE_NAME)
        except:
            print("[ERROR] Cannot update BUILD.pom [%s]: %s" % (build_pom_path, sys.exc_info()))
            raise

def update_released_artifact(root_path, packages, source_exclusions, new_version=None, new_artifact_hash=None, use_current_artifact_hash=False):
    """
    Updates the version and/or artifact hash attributes in the 
    BUILD.pom.released files in the specified packages.

    Creates the BUILD.pom.released file if it does not exist.
    """

    for package in packages:
        path = os.path.join(root_path, package, "BUILD.pom.released")
        try:
            if use_current_artifact_hash:
                assert new_artifact_hash is None
                artifact_hash = git.get_dir_hash(root_path, package, source_exclusions)
                assert artifact_hash is not None
            else:
                artifact_hash = new_artifact_hash

            content, _ = mdfiles.read_file(root_path, package, mdfiles.BUILD_POM_RELEASED_FILE_NAME)

            if content is not None:
                if new_version is not None:
                    content = _update_version_in_build_pom_released_content(content, new_version)
                if artifact_hash is not None:
                    content = _update_artifact_hash_in_build_pom_released_content(content, artifact_hash)
                mdfiles.write_file(content, root_path, package, mdfiles.BUILD_POM_RELEASED_FILE_NAME)

            else:
                if not os.path.exists(os.path.join(root_path, package)):
                    raise Exception("Bad package %s" % package)
                content = _get_build_pom_released_content(new_version, artifact_hash)
                mdfiles.write_file(content, root_path, package, mdfiles.BUILD_POM_RELEASED_FILE_NAME)
        except:            
            print("[ERROR] Cannot update BUILD.pom.released [%s]: %s" % (path, sys.exc_info()))
            raise

def _update_version_in_build_pom_content(build_pom_content, new_version):
    m = version.version_re.search(build_pom_content)
    assert m is not None
    return "%s%s%s" % (m.group(1), new_version.strip(), m.group(3))

version_incr_strat_re = re.compile("(^.*version_increment_strategy *= *[\"'])(.*?)([\"'].*)$", re.S)

def _update_version_incr_strategy_in_build_pom_content(build_pom_content, new_version_increment_strategy):
    m = version_incr_strat_re.search(build_pom_content)
    if m is None:
        build_pom_content += """
maven_artifact_update(
    version_increment_strategy = "%s",
)
"""
        return build_pom_content % new_version_increment_strategy.strip()
    else:
        return "%s%s%s" % (m.group(1), new_version_increment_strategy.strip(), m.group(3))

pom_generation_mode_re = re.compile("(^.*pom_generation_mode *= *[\"'])(.*?)([\"'].*)$", re.S)

def _update_pom_generation_mode_in_build_pom_content(build_pom_content, new_pom_generation_mode):
    value = new_pom_generation_mode.strip()
    m = pom_generation_mode_re.search(build_pom_content)
    if m is None:
        # add it to the end of maven_artifact
        maven_artifact = "maven_artifact("
        i = build_pom_content.index(maven_artifact)
        j = build_pom_content.index(")", i + len(maven_artifact))
        insert_at = j
        return build_pom_content[:insert_at] + \
            '    pom_generation_mode = "%s",%s' % (value, os.linesep) + \
                build_pom_content[insert_at:]
    else:
        return "%s%s%s" % (m.group(1), value, m.group(3))

def _add_pom_generation_mode_if_missing_in_build_pom_content(build_pom_content):
    m = pom_generation_mode_re.search(build_pom_content)
    if m is None:
        return _update_pom_generation_mode_in_build_pom_content(build_pom_content, pomgenmode.DEFAULT.name)
    else:
        return build_pom_content

def _update_version_in_build_pom_released_content(build_pom_released_content, new_released_version):
    m = version.version_re.search(build_pom_released_content)
    if m is None:
        raise Exception("Cannot find version in BUILD.pom.released")
    else:
        return "%s%s%s" % (m.group(1), new_released_version.strip(), m.group(3))

artifact_hash_re = re.compile("(^.*artifact_hash.*?=.*?[\"'])(.*?)([\"'].*)$", re.S)

def _update_artifact_hash_in_build_pom_released_content(build_pom_released_content, new_artifact_hash):
    m = artifact_hash_re.search(build_pom_released_content)
    if m is None:
        raise Exception("Cannot find artifact_hash in BUILD.pom.released")
    else:
        return "%s%s%s" % (m.group(1), new_artifact_hash.strip(), m.group(3))

def _get_build_pom_released_content(version, artifact_hash):
    assert version is not None, "version cannot be None"
    assert artifact_hash is not None, "artifact_hash cannot be None"
    content = """released_maven_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
    return content % (version.strip(), artifact_hash.strip())

def _get_version_qualifier_update_strategy(version_qualifier):
    version_qualifier = version_qualifier.strip()
    if version_qualifier.startswith("-"):
        version_qualifier = version_qualifier[1:]
    if version_qualifier.endswith("-"):
        version_qualifier = version_qualifier[:-1]
    return lambda current_version:"%s-%s" % (current_version, version_qualifier)

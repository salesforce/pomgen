"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is responsible for updating BUILD.pom and BUILD.pom.released files.
"""


import common.mdfiles as mdfiles
import common.genmode as genmode
import common.version as version
import common.version_increment_strategy as vis
import crawl.buildpom as buildpom
import crawl.git as git
import os
import re
import sys


def update_build_pom_file(root_path,
                          packages,
                          generation_strategy_factory,
                          new_version=None,
                          update_version_using_version_incr_strat=False,
                          new_version_incr_strat=None,
                          set_version_to_last_released_version=False,
                          version_qualifier_to_add=None,
                          version_qualifier_to_remove=None,
                          new_generation_mode=None,
                          add_generation_mode_if_missing=False):
    """
    If a non-None value is provided, updates the following values in BUILD.pom 
    files in the specified packages:
        - version (also version qualifier)
        - version_increment_strategy
        - generation_mode
    """
    for package in packages:
        strategy = generation_strategy_factory.get_strategy_for_package(package)
        assert strategy is not None, "Invalid package [%s]" % package
        build_pom_content, build_pom_path = mdfiles.read_file(root_path, package, strategy.metadata_path)
        try:
            current_version = version.parse_build_pom_version(build_pom_content)

            if current_version is None:
                # only possible if generation_mode=skip. this isn't quite
                # right, but we'll just ignore these type of packages
                # for simplicitly, because there isn't much metadata to
                # update anyway (only generation_mode is specified)
                continue

            updated_version = new_version


            # increment current version using version increment strategy
            if updated_version is None and update_version_using_version_incr_strat:
                is_snapshot_version = current_version.upper().endswith(vis.SNAPSHOT_QUAL)
                incr_strat_name = version.parse_version_increment_strategy_name(
                    build_pom_content)
                incr_strat = vis.get_version_increment_strategy(incr_strat_name)
                updated_version = incr_strat.get_next_development_version(current_version)
                if not is_snapshot_version:
                    # get_next_development_version re-adds -SNAPSHOT, but this
                    # wasn't a SNAPSHOT version to begin with, so remove that
                    # qualifier for consistency
                    updated_version = _remove_version_qualifier(updated_version, vis.SNAPSHOT_QUAL)


            # set version back to previously released version
            if updated_version is None and set_version_to_last_released_version:
                build_pom_released_content, _ = mdfiles.read_file(root_path, package, strategy.released_metadata_path)
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
                vq = _sanitize_version_qualifier(version_qualifier_to_add)
                if current_version.upper().endswith(vis.SNAPSHOT_QUAL):
                    # special case - we insert the new qualifer BEFORE -SNAPSHOT
                    updated_version = _insert_version_qualifier(current_version, vq)
                else:
                    updated_version = _append_version_qualifier(current_version, vq)

            # remove version qualifier from current version
            if updated_version is None and version_qualifier_to_remove is not None:
                updated_version = _remove_version_qualifier(current_version, version_qualifier_to_remove)


            if updated_version is not None:
                build_pom_content = _update_version_in_build_pom_content(build_pom_content, updated_version)
            if new_version_incr_strat is not None:
                build_pom_content = _update_version_incr_strategy_in_build_pom_content(build_pom_content, new_version_incr_strat)
            if new_generation_mode is not None:
                build_pom_content = _update_generation_mode_in_build_pom_content(build_pom_content, new_generation_mode)
            if add_generation_mode_if_missing:
                build_pom_content = _add_generation_mode_if_missing_in_build_pom_content(build_pom_content)
                    
            mdfiles.write_file(build_pom_content, root_path, package, strategy.metadata_path)
        except:
            print("[ERROR] Cannot update BUILD.pom [%s]: %s" % (build_pom_path, sys.exc_info()))
            raise


def update_released_artifact(root_path, packages, generation_strategy_factory,
                             source_exclusions,
                             new_version=None,
                             new_artifact_hash=None,
                             use_current_artifact_hash=False):
    """
    Updates the version and/or artifact hash attributes in the 
    BUILD.pom.released files in the specified packages.

    Creates the BUILD.pom.released file if it does not exist.
    """
    for package in packages:
        strategy = generation_strategy_factory.get_strategy_for_package(package)
        assert strategy is not None, "Invalid package [%s]" % package

        released_file_path = strategy.released_metadata_path
        content, _ = mdfiles.read_file(root_path, package, released_file_path)
        if content is None and new_artifact_hash is None:
            # there is no released md file yet and a hash was not specified
            # explicitly: we have to compute the current hash so we can gen
            # the file below
            use_current_artifact_hash = True

        if use_current_artifact_hash:
            assert new_artifact_hash is None
            # we need to load the BUILD.pom file to see whether additional
            # packages are specified
            packages = [package]
            art_def = buildpom.parse_maven_artifact_def(root_path, package, strategy)
            if art_def is not None:
                # if the BUILD.pom file doesn't exist, then by definition
                # additional packages cannot have been specified
                packages += art_def.additional_change_detected_packages
            artifact_hash = git.get_dir_hash(root_path, packages, source_exclusions)
            assert artifact_hash is not None
        else:
            artifact_hash = new_artifact_hash

        try:
            if content is None:
                content = _get_build_pom_released_content(new_version, artifact_hash)
            else:
                if new_version is not None:
                    content = _update_version_in_build_pom_released_content(content, new_version)
                if artifact_hash is not None:
                    content = _update_artifact_hash_in_build_pom_released_content(content, artifact_hash)
            mdfiles.write_file(content, root_path, package, released_file_path)
        except:            
            print("[ERROR] Cannot update released manifest [%s]: %s" % (released_file_path, sys.exc_info()))
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
artifact_update(
    version_increment_strategy = "%s",
)
"""
        return build_pom_content % new_version_increment_strategy.strip()
    else:
        return "%s%s%s" % (m.group(1), new_version_increment_strategy.strip(), m.group(3))

generation_mode_re = re.compile("(^.*generation_mode *= *[\"'])(.*?)([\"'].*)$", re.S)


def _update_generation_mode_in_build_pom_content(build_pom_content, new_generation_mode):
    value = new_generation_mode.strip()
    m = generation_mode_re.search(build_pom_content)
    if m is None:
        # add it to the end of maven_artifact
        artifact_rule_name = "maven_artifact("
        i = build_pom_content.find(artifact_rule_name)
        if i == -1:
            artifact_rule_name = "artifact("
            i = build_pom_content.index(artifact_rule_name)
        j = build_pom_content.index(")", i + len(artifact_rule_name))
        insert_at = j
        return build_pom_content[:insert_at] + \
            '    generation_mode = "%s",%s' % (value, os.linesep) + \
                build_pom_content[insert_at:]
    else:
        return "%s%s%s" % (m.group(1), value, m.group(3))


def _add_generation_mode_if_missing_in_build_pom_content(build_pom_content):
    m = generation_mode_re.search(build_pom_content)
    if m is None:
        return _update_generation_mode_in_build_pom_content(build_pom_content, genmode.DEFAULT.name)
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
    assert version is not None, "a released version must be specified, use --new_released_version"
    assert artifact_hash is not None, "artifact_hash cannot be None"
    content = """released_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
    return content % (version.strip(), artifact_hash.strip())


def _sanitize_version_qualifier(version_qualifier):
    version_qualifier = version_qualifier.strip()
    if version_qualifier.startswith("-"):
        version_qualifier = version_qualifier[1:]
    if version_qualifier.endswith("-"):
        version_qualifier = version_qualifier[:-1]
    return version_qualifier


def _append_version_qualifier(current_version, version_qualifier):
    if current_version.endswith(version_qualifier):
        # we won't re-append the same qualifier ...
        return current_version
    else:
        return "%s-%s" % (current_version, version_qualifier)


def _insert_version_qualifier(current_version, version_qualifier):
    if current_version.endswith(version_qualifier):
        # we won't insert the same qualifier
        return current_version
    else:
        i = current_version.rfind("-")
        return "%s-%s-%s" % (current_version[0:i], version_qualifier,
                             current_version[i+1:])


def _remove_version_qualifier(current_version, version_qualifier):
    if not version_qualifier.startswith("-"):
        version_qualifier = "-%s" % version_qualifier
    # if the given version qualifier (vq) is a prefix of an existing vq in
    # the version string, the entire matching vq will be removed
    i = current_version.find(version_qualifier)
    if i == -1:
        return current_version
    # current_version: abc-rel9
    # version_qualifier: -rel
    # i = 3
    # end_index = 3 + 4 = 7
    end_index = i + len(version_qualifier)
    if end_index == len(current_version) or current_version[end_index-1] == "-":
        # the given version_qualifier matches a vq in the current version
        pass
    else:
        # the given version_qualifier matches the beginning of a vq in the
        # current version - find the end_index
        end_index = current_version.find("-", end_index)
        if end_index == -1:
            end_index = len(current_version)
    return current_version[:i] + current_version[end_index:]

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is responsible for updating metadata files, such as BUILD.pom and
BUILD.pom.released
"""


import common.code as code
import common.common as common
import common.mdfiles as mdfiles
import common.version_increment_strategy as vis
import crawl.buildpom as buildpom
import crawl.git as git
import os
import re
import sys


version_re = re.compile("(^.*version *= *[\"'])(.*?)([\"'].*)$", re.S)
artifact_hash_re = re.compile("(^.*artifact_hash.*?=.*?[\"'])(.*?)([\"'].*)$", re.S)


def update_artifact(root_path, packages, workspace,
                    new_version=None,
                    update_version_using_incr_strat=False,
                    new_version_incr_strat=None,
                    set_version_to_last_released_version=False,
                    version_qualifier_to_add=None,
                    version_qualifier_to_remove=None):
    for package in packages:
        _maybe_update_version(root_path, package, workspace,
                              new_version,
                              update_version_using_incr_strat,
                              set_version_to_last_released_version,
                              version_qualifier_to_add,
                              version_qualifier_to_remove)
        _maybe_update_version_incr_strat(root_path, package, workspace, new_version_incr_strat)
            

def update_released_artifact(root_path, packages, generation_strategy_factory,
                             source_exclusions,
                             new_version=None,
                             new_artifact_hash=None,
                             use_current_artifact_hash=False):
    """
    Updates the version and/or artifact hash attributes in the released
    metadata files (ie BUILD.pom.released) in the specified packages.

    Creates the released metadata file if it does not exist.
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
                content = _get_released_metadata(new_version, artifact_hash)
            else:
                if new_version is not None:
                    content = _update_version_in_released_metadata(content, new_version)
                if artifact_hash is not None:
                    content = _update_artifact_hash_in_released_metadata(content, artifact_hash)
            mdfiles.write_file(content, root_path, package, released_file_path)
        except:            
            print("[ERROR] Cannot update released manifest [%s]: %s" % (released_file_path, sys.exc_info()))
            raise


def _maybe_update_version(root_path, package, workspace,
                          updated_version,
                          update_version_using_incr_strat,
                          set_version_to_last_released_version,
                          version_qualifier_to_add,
                          version_qualifier_to_remove):
    if (updated_version is None and
        not update_version_using_incr_strat and
        not set_version_to_last_released_version and
        version_qualifier_to_add is None and
        version_qualifier_to_remove is None):
        return
        
    art_def = workspace.parse_maven_artifact_def(package)
    assert art_def is not None
    current_version = art_def.version
    if update_version_using_incr_strat:
        is_snapshot_version = current_version.upper().endswith(vis.SNAPSHOT_QUAL)
        incr_strat = vis.get_version_increment_strategy(art_def.version_increment_strategy_name)
        updated_version = incr_strat.get_next_development_version(current_version)
        if not is_snapshot_version:
            # get_next_development_version re-adds -SNAPSHOT, but this
            # wasn't a SNAPSHOT version to begin with, so remove that
            # qualifier for consistency
            updated_version = _remove_version_qualifier(updated_version, vis.SNAPSHOT_QUAL)
    if set_version_to_last_released_version and art_def.released_version is not None:
        updated_version = art_def.released_version
    if version_qualifier_to_add is not None:
        vq = _sanitize_version_qualifier(version_qualifier_to_add)
        if current_version.upper().endswith(vis.SNAPSHOT_QUAL):
            # special case - we insert the new qualifer BEFORE -SNAPSHOT
            updated_version = _insert_version_qualifier(current_version, vq)
        else:
            updated_version = _append_version_qualifier(current_version, vq)
    if version_qualifier_to_remove is not None:
        updated_version = _remove_version_qualifier(current_version, version_qualifier_to_remove)

    if updated_version is not None and current_version != updated_version:
        _update_attr_value(root_path, art_def, "version", updated_version)


def _maybe_update_version_incr_strat(root_path, package, workspace, updated_version_incr_strat):
    if updated_version_incr_strat is not None:
        art_def = workspace.parse_maven_artifact_def(package)        
        assert art_def is not None
        if art_def.version_increment_strategy_name != updated_version_incr_strat:
            _update_attr_value(root_path, art_def, "version_increment_strategy", updated_version_incr_strat)


def _update_attr_value(root_path, art_def, attr_name, updated_value):
    assert art_def is not None
    assert updated_value is not None
    if isinstance(updated_value, str):
        updated_value = '"' + updated_value + '"'
    md_file_path = art_def.get_md_file_path_for_attr(attr_name)
    path = os.path.join(root_path, md_file_path)
    content = common.read_file(path)
    _, value_indexes = code.parse_artifact_attributes(content)
    start, end = value_indexes[attr_name]
    updated_content = content[:start] + updated_value + content[end+1:]
    common.write_file(path, updated_content)


def _update_version_in_released_metadata(build_pom_released_content, new_released_version):
    m = version_re.search(build_pom_released_content)
    if m is None:
        raise Exception("Cannot find version in BUILD.pom.released")
    else:
        return "%s%s%s" % (m.group(1), new_released_version.strip(), m.group(3))


def _update_artifact_hash_in_released_metadata(build_pom_released_content, new_artifact_hash):
    m = artifact_hash_re.search(build_pom_released_content)
    if m is None:
        raise Exception("Cannot find artifact_hash in BUILD.pom.released")
    else:
        return "%s%s%s" % (m.group(1), new_artifact_hash.strip(), m.group(3))


def _get_released_metadata(version, artifact_hash):
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

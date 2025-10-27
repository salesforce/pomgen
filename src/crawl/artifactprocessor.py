"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Attaches additional metadata to maven_artifact instances.  

This logic could run during BUILD.pom[.released] parsing, but it feels a bit
too heavy (things like running git...). Separating it into its own module also 
helps with testing.
"""

import common.code as code
from common import mdfiles
from crawl import git
from crawl import releasereason
import os


def augment_artifact_def(repo_root_path,
                         art_def,
                         source_exclusions,
                         change_detection_enabled):

    # library path
    art_def.library_path = _get_library_path(repo_root_path, art_def)

    # attributes that are set at the library level
    _set_library_level_attribute_values(repo_root_path, art_def)

    # release state
    if art_def.released_version is None or art_def.released_artifact_hash is None:
        # never released?
        art_def.requires_release = True
        art_def.release_reason = releasereason.FIRST
    else:
        if change_detection_enabled and art_def.change_detection:
            has_changed = _has_changed_since_last_release(repo_root_path, art_def, source_exclusions)
            if has_changed:
                art_def.requires_release = True
                art_def.release_reason = releasereason.ARTIFACT
            else:
                # check for local edits - if found, set requires_release -
                # this is to support a better local dev experience
                local_edits = git.has_uncommitted_changes(repo_root_path, art_def.bazel_package, source_exclusions)
                if local_edits:
                    art_def.requires_release = True
                    art_def.release_reason = releasereason.UNCOMMITTED_CHANGES
                else:
                    art_def.requires_release = False
        else:
            art_def.requires_release = True
            art_def.release_reason = releasereason.ALWAYS

    return art_def


def _get_library_path(repo_root_path, art_def):
    return mdfiles.get_library_root_package(
        repo_root_path, art_def.bazel_package, art_def.generation_strategy)[0]


def _set_library_level_attribute_values(repo_root_path, art_def):
    """
    Values that apply to all artifacts (group/version etc) may be set in
    the LIBRARY.root file.
    """
    assert art_def.library_path is not None
    md_dir_name = os.path.dirname(art_def.generation_strategy.metadata_path)
    lib_md_file_rel_path = os.path.join(art_def.library_path, md_dir_name, mdfiles.LIB_ROOT_FILE_NAME)
    content, _ = mdfiles.read_file(repo_root_path, lib_md_file_rel_path, must_exist=True)
    ma = code.get_function_block(content, "artifact")
    if ma is not None:
        ma_attrs, _ = code.parse_attributes(ma)
        for attr_name in ("group_id", "version",):
            lib_value = ma_attrs.get(attr_name, None)
            if lib_value is not None:
                # we don't allow the attr to be set at multiple levels
                assert getattr(art_def, attr_name) is None, (
                    "The attr [%s] cannot be both set in the library root file and the " \
                    "metadata file at [%s]" % (attr_name, art_def.bazel_package))
                setattr(art_def, attr_name, lib_value)
                art_def.register_md_file_path_for_attr(attr_name, lib_md_file_rel_path)
                


def _has_changed_since_last_release(repo_root_path, art_def, source_exclusions):
    all_packages = [art_def.bazel_package] + art_def.additional_change_detected_packages
    current_artifact_hash = git.get_dir_hash(repo_root_path, all_packages,
                                             source_exclusions)

    assert current_artifact_hash is not None

    return current_artifact_hash != art_def.released_artifact_hash

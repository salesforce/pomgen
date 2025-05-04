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

from common import logger
from common import mdfiles
from crawl import git
from crawl import releasereason
import os


def augment_artifact_def(repo_root_path,
                         art_def,
                         source_exclusions,
                         change_detection_enabled):
    art_def.library_path = _get_library_path(repo_root_path, art_def)

    if art_def.released_version is None or art_def.released_artifact_hash is None:
        # never released?
        art_def.requires_release = True
        art_def.release_reason = releasereason.ReleaseReason.FIRST
    else:
        if change_detection_enabled and art_def.change_detection:
            has_changed = _has_changed_since_last_release(repo_root_path, art_def, source_exclusions)
            if has_changed:
                art_def.requires_release = True
                art_def.release_reason = releasereason.ReleaseReason.ARTIFACT
            else:
                # check for local edits - if found, set requires_release -
                # this is to support a better local dev experience
                local_edits = git.has_uncommitted_changes(repo_root_path, art_def.bazel_package, source_exclusions)
                if local_edits:
                    art_def.requires_release = True
                    art_def.release_reason = releasereason.ReleaseReason.UNCOMMITTED_CHANGES
                else:
                    art_def.requires_release = False
        else:
            art_def.requires_release = True
            art_def.release_reason = releasereason.ReleaseReason.ALWAYS
    return art_def


def _get_library_path(repo_root_path, art_def):
    """
    Starts at the path the specified artifact lives at and "walks up" to find  
    the location (path) of the library owning the specified artifact.
    """
    abs_repo_path = os.path.abspath(repo_root_path)
    org_abs_path = os.path.abspath(os.path.join(repo_root_path, art_def.bazel_package))
    path = org_abs_path
    emergency_break = 0
    while True:
        if mdfiles.is_library_package(path):
            return os.path.relpath(path, repo_root_path)
        if path == abs_repo_path:
            raise Exception("Did not find %s at %s or any parent dir" % (mdfiles.LIB_ROOT_FILE_NAME, org_abs_path))
        path = os.path.dirname(path)
        assert emergency_break < 50 # just in case
        emergency_break += 1


def _has_changed_since_last_release(repo_root_path, art_def, source_exclusions):
    all_packages = [art_def.bazel_package] + art_def.additional_change_detected_packages
    current_artifact_hash = git.get_dir_hash(repo_root_path, all_packages,
                                             source_exclusions)

    assert current_artifact_hash is not None

    return current_artifact_hash != art_def.released_artifact_hash

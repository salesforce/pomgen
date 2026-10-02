"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import common.logger as logger
import os
import subprocess


def get_next_available_version(artifacts, version, nexus_artifact_url, vers_incr_strat, verbose=False):
    """
    Starting from the current version of the given artifacts, increments
    using the provided version increment strategy until a version is found
    that does not exist in Nexus for any of the artifacts.

    Returns the first available version string.
    """
    _check_artifacts_sanity(artifacts)
    while not _is_version_available(artifacts, version, nexus_artifact_url, verbose):
        version = vers_incr_strat.get_next_release_version(version)
    return version


def _is_version_available(artifacts, version, nexus_artifact_url, verbose):
    """
    Checks whether the version is available (does not exist in Nexus) for
    all given artifacts.

    Input: a list of artifact defs that all belong to the same library.
    Returns True if none of the artifacts exist at their current version,
    False if at least one already exists.
    """
    urls = []
    for art_def in artifacts:
        group_path = art_def.group_id.replace(".", "/")
        path = "%s/%s/%s/%s/%s-%s.pom" % (
            nexus_artifact_url, group_path, art_def.artifact_id,
            version, art_def.artifact_id, version)
        urls.append(path)
    if nexus_artifact_url.startswith("file://"):
        found = _check_paths_exist(urls, verbose)
    elif nexus_artifact_url.startswith("http"):
        found = _head_requests(urls, verbose)
    else:
        raise AssertionError("Unknown scheme for nexus url [%s]" % nexus_artifact_url)
    if found:
        # at least one of the artifacts exists, so this version is not available
        return False
    else:
        return True


def _check_paths_exist(urls, verbose):
    """
    Returns True if at least one of the urls, treated as local paths,
    exist.
    """
    paths = [os.path.expanduser(p[len("file://"):]) for p in urls]
    for path in paths:
        if verbose:
            logger.debug("Checking path: %s" % path)
        if os.path.exists(path):
            return True
    return False


def _head_requests(urls, verbose):
    """
    Issues HEAD requests for the given urls in parallel.
    Returns True if at least one request was successful (http code 200).
    """
    procs = []
    for url in urls:
        cmd = ["curl", "-s", "--netrc", "-L", "--head",
               "-o", "/dev/null", "-w", "%{http_code}", url]
        if verbose:
            logger.debug("Running [%s]" % " ".join(cmd))
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procs.append(proc)

    found = False
    for proc in procs:
        stdout, _ = proc.communicate()
        if stdout.decode().strip() == "200":
            found = True
    return found


def _check_artifacts_sanity(artifacts):
    """
    All artifact defs must be for the same lib, at the same version.
    """
    version = artifacts[0].version
    library_path = artifacts[0].library_path
    for art_def in artifacts:
        assert art_def.version == version, "All artifacts must have the same version, got %s and %s" % (version, art_def.version)
        assert art_def.library_path == library_path, "All artifacts must belong to the same library, got %s and %s" % (library_path, art_def.library_path)

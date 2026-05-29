"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import common.logger as logger
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
        url = "%s/%s/%s/%s/%s-%s.pom" % (
            nexus_artifact_url, group_path, art_def.artifact_id,
            version, art_def.artifact_id, version)
        urls.append(url)

    results = _head_requests(urls, verbose)

    for http_code in results:
        if http_code == "200":
            return False
    return True


def _check_artifacts_sanity(artifacts):
    """
    # just a sanity check - all artifact defs must be for the same lib,
    at the same version!
    """
    version = artifacts[0].version
    library_path = artifacts[0].library_path
    for art_def in artifacts:
        assert art_def.version == version, "All artifacts must have the same version, got %s and %s" % (version, art_def.version)
        assert art_def.library_path == library_path, "All artifacts must belong to the same library, got %s and %s" % (library_path, art_def.library_path)


def _head_requests(urls, verbose):
    """
    Issues HEAD requests for the given urls in parallel.
    Returns a list of HTTP status codes (as strings), one per url.
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

    results = []
    for proc in procs:
        stdout, _ = proc.communicate()
        results.append(stdout.decode().strip())
    return results

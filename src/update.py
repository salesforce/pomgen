"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Command line utility that updates attributes in metadata files.
"""

from common import argsupport
from common import common
from common import manifestcontent as manifestcontent
from common import metadataupdate
from common import version_increment_strategy as vis
from config import config
from generate import generationstrategyfactory
import crawl.workspace as workspace
import argparse
import sys


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Updates artifact metadata")
    parser.add_argument("--package", type=str, required=True,
        help="Updates metadata files under the specified package(s). " + argsupport.get_package_doc())

    parser.add_argument("--new_version", type=str, required=False,
        help="The value of the current version")
    parser.add_argument("--new_version_increment_strategy", type=str,
        required=False, choices = vis.VERSION_INCREMENT_STRATEGIES,
        help="The value of the version_increment_strategy")
    parser.add_argument("--new_released_version", type=str, required=False,
        help="The value of the released version")
    parser.add_argument("--new_released_artifact_hash", type=str, required=False,
        help="The value of the released artifact hash")
    parser.add_argument("--update_released_artifact_hash_to_current", required=False,
                        action='store_true',
        help="Computes the artifact hash based on the current state")
    parser.add_argument("--update_version_using_version_increment_strategy", required=False,
                        action='store_true',
        help="Updates the version using the increment strategy set in the manifest file")
    parser.add_argument("--set_version_to_last_released", required=False,
                        action='store_true',
        help="Sets the version in manifest file to the last released version specified in the released metadata file")
    parser.add_argument("--add_version_qualifier", required=False, type=str,
        help="Adds the specified string to the end of the version, using '-' as a separator. If the version ends with \"-SNAPSHOT\", the specified qualifier is added before the snapshot suffix")
    parser.add_argument("--remove_version_qualifier", required=False, type=str,
        help="Removes the specified version qualifier from the version")
    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")

    parser.add_argument("--repo_root", type=str, required=False,
        help="the root of the repository")    
    return parser.parse_args(args)


if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root)
    fac = generationstrategyfactory.GenerationStrategyFactory(
        repo_root, cfg, manifestcontent.NOOP, verbose=args.verbose)
    ws = workspace.Workspace(repo_root, cfg, fac, cache_artifact_defs=False)
    packages = argsupport.get_all_packages(repo_root, args.package, fac, verbose=args.verbose)
    assert len(packages) > 0, "Did not find any packages at [%s]" % args.package

    if (args.new_version is not None or
        args.update_version_using_version_increment_strategy or
        args.set_version_to_last_released or
        args.add_version_qualifier is not None or
        args.remove_version_qualifier is not None or
        args.new_version_increment_strategy is not None):

        metadataupdate.update_artifact(
            repo_root, packages, ws,
            args.new_version,
            args.update_version_using_version_increment_strategy,
            args.new_version_increment_strategy,
            args.set_version_to_last_released,
            args.add_version_qualifier,
            args.remove_version_qualifier)

    if (args.new_released_version is not None or
        args.new_released_artifact_hash is not None or
        args.update_released_artifact_hash_to_current):
        metadataupdate.update_released_artifact(
            repo_root, packages, fac,
            cfg.all_src_exclusions,
            args.new_released_version,
            args.new_released_artifact_hash,
            args.update_released_artifact_hash_to_current)

#!/usr/bin/env python

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Command line utility that updates attributes in BUILD.pom and 
BUILD.pom.released files.
"""

from common import argsupport
from common import common
from common import logger
from common import mdfiles
from config import config
from crawl import bazel
from update import buildpomupdate
import argparse
import os
import sys

VERSION_INCREMENT_STRATEGIES = ("major", "minor", "patch",)

def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Updates Maven artifact metadata")
    parser.add_argument("--package", type=str, required=True,
        help="Updates BUILD.pom files under the specified package(s). " + argsupport.get_package_doc())

    parser.add_argument("--new_version", type=str, required=False,
        help="The value of the version to write into BUILD.pom files")
    parser.add_argument("--new_version_increment_strategy", type=str,
        required=False, choices = VERSION_INCREMENT_STRATEGIES,
        help="The value of the version_increment_strategy to write into BUILD.pom files")
    parser.add_argument("--new_released_version", type=str, required=False,
        help="The value of the version to write into BUILD.pom.released files")
    parser.add_argument("--new_released_artifact_hash", type=str, required=False,
        help="The value of the artifact_hash to write into BUILD.pom.released files")
    parser.add_argument("--update_released_artifact_hash_to_current", required=False,
                        action='store_true',
        help="Writes the value of the current artifact hash under the specified package into the BUILD.pom.released file")
    parser.add_argument("--update_version_using_version_increment_strategy", required=False,
                        action='store_true',
        help="Updates the version in BUILD.pom files, by incrementing it using the version_increment_strategy specified in the same file")
    parser.add_argument("--set_version_to_last_released", required=False,
                        action='store_true',
        help="Updates the version in BUILD.pom files, by setting it to the last released version specified in the corresponding BUILD.pom.released files")
    parser.add_argument("--add_version_qualifier", required=False, type=str,
        help="Adds the specified string to the end of the version, using '-' as a separator. If the version ends with \"-SNAPSHOT\", the specified qualifier is added before the snapshot suffix")
    parser.add_argument("--move_md_files", required=False, type=str,
        help="Moves metadata files from 'src_dir' to 'dest_dir' for each package being processed. Format: <src_dir>,<dest_dir>")

    parser.add_argument("--repo_root", type=str, required=False,
        help="the root of the repository")    
    parser.add_argument("--dry_run", required=False, action='store_true',
        help="do as much work as possible without actually updating BUILD.poms")
    return parser.parse_args(args)

if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root)
    packages = argsupport.get_all_packages(repo_root, args.package)
    if len(packages) == 0:
        raise Exception("Did not find any BUILD.pom packages at [%s]" % args.package)

    if args.dry_run:
        logger.info("Dry run enabled")
    else:
        if (args.new_version is not None or
            args.update_version_using_version_increment_strategy or
            args.set_version_to_last_released or
            args.add_version_qualifier is not None or
            args.new_version_increment_strategy is not None):

            buildpomupdate.update_build_pom_file(
                repo_root, packages, args.new_version,
                args.update_version_using_version_increment_strategy,
                args.new_version_increment_strategy,
                args.set_version_to_last_released,
                args.add_version_qualifier)

        if (args.new_released_version is not None or
            args.new_released_artifact_hash is not None or
            args.update_released_artifact_hash_to_current):
            buildpomupdate.update_released_artifact(
                repo_root, packages, cfg.all_src_exclusions,
                args.new_released_version,
                args.new_released_artifact_hash,
                args.update_released_artifact_hash_to_current)

        if args.move_md_files is not None:
            src_dir, dest_dir = args.move_md_files.split(",")
            # we also need to include the library level metadata
            all_packages = packages + bazel.query_all_libraries(repo_root, packages)
            mdfiles.move_files(repo_root, all_packages, src_dir, dest_dir)

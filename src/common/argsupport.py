"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Common argument processing.
"""
from common import logger
import os


def get_package_doc():
    """
    Doc  for the common --package argument.
    """
    return "Multiple comma-separated paths are supported. Each path is crawled, looking for packages. If a path starts with  '-', packages starting with that path are excluded. If not specified, defaults to the repository root."


def get_all_packages(repository_root_path, packages_str, 
                     generation_stategy_factory, verbose=False):
    """
    Handles the common --package argument.

    Given the specified packages string, returns all matching Bazel packages
    under the specified repository root path.
    
    The packages string supports the following formats:
       - A single path, relative from the repository root, for example:
         projects/libs/scone
       - Multiple, comma-separated paths, relative from the repository root,
         for example: projects/libs/scone,projects/libs/servicelibs,srpc,...
       - A relative path may start with '-' to mean it should be excluded,
         for example: projects/libs,-projects/libs/scone
         The above means: "all packages under projects/libs, excluding the ones
         under projects/libs/scone
    """
    if packages_str is None:
        packages_str = "."
    all_paths = [p.strip() for p in packages_str.split(",")]
    inclusion_paths = _to_path([p[1:] if p.startswith("+") else p for p in all_paths if not p.startswith("-")])
    exclusion_paths = _to_path([p[1:] for p in all_paths if p.startswith("-")])

    # we'll maintain discovery order because that seems like a nice thing to do
    packages_list = []
    all_packages = set()

    for p in inclusion_paths:
        packages = _find_packages_with_md(
            repository_root_path, p, generation_stategy_factory, verbose)
        for package in packages:
            for exclusion_path in exclusion_paths:
                prefix_match = True
                if exclusion_path.endswith("/"):
                    exclusion_path = exclusion_path[:-1]
                    prefix_match = False
                if package.startswith(exclusion_path):
                    if prefix_match or package.endswith(exclusion_path):
                        break
            else:
                if package not in all_packages:
                    all_packages.add(package)
                    packages_list.append(package)

    return packages_list


def _find_packages_with_md(repository_root_path, target_pattern, fac, verbose):
    """
    Returns all packages in the specified target pattern, as a list of strings,
    that are "maven aware" packages.
    """
    path = os.path.join(repository_root_path, _target_pattern_to_path(target_pattern))

    maven_artifact_packages = []
    for rootdir, dirs, files in os.walk(path):
        if verbose:
            logger.debug("Checking for artifact package at [%s]" % rootdir)
        if fac.get_strategy_for_package(rootdir) is not None:
            relpath = os.path.relpath(rootdir, repository_root_path)
            if verbose:
                logger.debug("Found artifact package [%s]" % relpath)
            maven_artifact_packages.append(relpath)
    return maven_artifact_packages


def _to_path(list_of_paths):
    return [_target_pattern_to_path(p) for p in list_of_paths]
    

def _target_pattern_to_path(target_pattern):
    """
    Converts a bazel target pattern to a directory path.

    For example:
        //projects/libs/servicelibs/srpc/srpc-api:srpc-api -> projects/libs/servicelibs/srpc/srpc-api
        //projects/libs/servicelibs/srpc/... -> projects/libs/servicelibs/srpc
    """
    if target_pattern.startswith("//"):
        target_pattern = target_pattern[2:]
    elif target_pattern.startswith("/"):
        target_pattern = target_pattern[1:]
    if ":" in target_pattern:
        target_pattern = target_pattern[0:target_pattern.rfind(":")]
    if target_pattern.endswith("/..."):
        target_pattern = target_pattern[0:-4]
    return target_pattern

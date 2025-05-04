"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Common argument processing.
"""
from crawl import bazel

def get_package_doc():
    """
    Doc  for the common --package argument.
    """
    return "Multiple comma-separated paths are supported. Each path is crawled, looking for packages. If a path starts with  '-', packages starting with that path are excluded. If not specified, defaults to the repository root."

def get_all_packages(repository_root_path, packages_str, verbose=False):
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
        packages = bazel.query_all_artifact_packages(repository_root_path, p, verbose)
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

def _to_path(list_of_paths):
    return [bazel.target_pattern_to_path(p) for p in list_of_paths]
    

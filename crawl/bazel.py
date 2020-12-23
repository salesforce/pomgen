"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module has methods that return information about the monorepo structure.

Whenever possible, the code here delegates to "bazel query" to gather the
requested data.
"""

from common import mdfiles
from common.os_util import run_cmd
from common import logger
import os
import json


def query_java_library_deps_attributes(repository_root_path, target_pattern):
    """
    Returns, as a list of strings, the combined values of the 'deps' and 
    'runtime_deps' attributes on the java_library rule identified by the 
    specified target_pattern.

    Example return value:

        ["@com_google_guava_guava//jar",
         "@com_github_ben_manes_caffeine_caffeine//jar",
         "//projects/libs/servicelibs/srpc/srpc-api"]

    If the target name is not specified explicitly, it is defaulted based on 
    the package name.

    target_pattern examples:
      - //projects/libs/foo:blah 
        -> look for a target called "blah" in the "foo" package
      - //projects/libs/foo 
        -> look for a target called "foo" in the "foo" package (the target name
           is defaulted based on the package name)
    """
    if target_pattern.endswith("..."):
        raise Exception("target_pattern must be more specific")

    dep_attributes = ("deps", "runtime_deps")
    query_parts = ["labels(%s, %s)" % (attr, target_pattern) for attr in dep_attributes]
    query = "bazel query --noimplicit_deps --order_output full '%s'" % " union ".join(query_parts)
    output = run_cmd(query, cwd=repository_root_path).splitlines()
    deps = _sanitize_deps(output)
    deps = _ensure_unique_deps(deps)
    return reversed(deps)


def query_all_artifact_packages(repository_root_path, target_pattern):
    """
    Returns all packages in the specified target pattern, as a list of strings,
    that are "maven aware" packages.
    """
    path = os.path.join(repository_root_path, target_pattern_to_path(target_pattern))

    maven_artifact_packages = []
    for rootdir, dirs, files in os.walk(path):
        if mdfiles.is_artifact_package(rootdir):
            maven_artifact_packages.append(os.path.relpath(rootdir, repository_root_path))
    return maven_artifact_packages


def query_all_libraries(repository_root_path, packages):
    """
    Given a list of (BUILD.pom) packages, walks the paths up to find the root
    library directories, and returns those (without duplicates).
    """
    lib_roots = []
    for org_package in packages:
        for lib_root in lib_roots:
            if org_package.startswith(lib_root):
                break # we already have the path for this library
        else:
            package = org_package
            while len(package) > 0 and package != '/':
                abs_package_path = os.path.join(repository_root_path, package)
                if mdfiles.is_library_package(abs_package_path):
                    lib_roots.append(package)
                    break
                else:
                    package = os.path.dirname(package)

    return lib_roots


def query_maven_install(json_file_path):
    """
    Return a list of strings each a Maven "coord"* from the specified "pinned" 
    dependencies json file.

    * group_id:artifact_id:[packaging]:[classifier]:version
    """
    all_coords = []
    logger.info("Processing pinned dependencies [%s]" % json_file_path)
    with open(json_file_path, "r") as install_input:
        install_json = json.load(install_input)
        json_deps = install_json["dependency_tree"]["dependencies"]
        for json_dep in json_deps:
            all_coords.append(json_dep["coord"])
    return all_coords


def target_pattern_to_path(target_pattern):
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


def _sanitize_deps(deps):
    updated_deps = []
    for dep in deps:
        sanitized = _sanitize_dep(dep)
        if sanitized is not None:
            updated_deps.append(dep)
    return updated_deps


def _sanitize_dep(dep):
    if dep.startswith('@'):
        if dep.endswith(":jar"):
            return dep[:-4] # remove :jar suffix
        dep_split = dep.split(':')
        if len(dep_split) == 2 and len(dep_split[1]) > 0:
            return dep_split[1]
    elif dep.startswith("//"):
        return dep
    # dep is not something we want, ignore (e.g. log lines from tools/bazel can fall into here)
    return None


def _ensure_unique_deps(deps):
    updated_deps = []
    s = set()
    for dep in deps:
        if dep not in s:
            updated_deps.append(dep)
            s.add(dep)
    return updated_deps

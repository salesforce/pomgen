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
from crawl import dependency
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


def query_all_artifact_packages(repository_root_path, target_pattern, verbose=False):
    """
    Returns all packages in the specified target pattern, as a list of strings,
    that are "maven aware" packages.
    """
    path = os.path.join(repository_root_path, target_pattern_to_path(target_pattern))

    maven_artifact_packages = []
    for rootdir, dirs, files in os.walk(path):
        if verbose:
            logger.debug("Checking for artifact package at [%s]" % rootdir)
        if mdfiles.is_artifact_package(rootdir):
            relpath = os.path.relpath(rootdir, repository_root_path)
            if verbose:
                logger.debug("Found artifact package [%s]" % relpath)
            maven_artifact_packages.append(relpath)
    return maven_artifact_packages


def query_all_libraries(repository_root_path, packages, verbose=False):
    """
    Given a list of packages (directories), walks the paths up to find the root
    library directories, and returns those (without duplicates).
    """
    lib_roots = set()
    for package in packages:
        while len(package) > 0 and package != '/':
            abs_package_path = os.path.join(repository_root_path, package)
            if verbose:
                logger.debug("Checking path for library [%s]" % abs_package_path)
            if mdfiles.is_library_package(abs_package_path):
                if verbose:
                    logger.debug("Found library [%s]" % package)
                lib_roots.add(package)
                break
            else:
                package = os.path.dirname(package)
    return sorted(lib_roots)


def _normalize_dependency_string_to_group_id_artifact_id(dependency):
    return ":".join(dependency.split(":")[:2]) # remove classifier/package, so we can grab version from artifacts list


def parse_maven_install(mvn_install_name, json_file_path):
    """
    Returns a list of tuples, one item for each dependency managed by the 
    specified maven_install json file: (dep, transitives, exclusions)

        dep: dependency.Dependency instance managed by the maven_install rule
        transitives: for the dep, the transitive closure of dependencies, as
                     list of dependency.Dependency instances
        exclusions: for the dep, the transitives that are explicitly excluded,
                    as a list of dependency.Dependency instances
    """
    result = []
    with open(json_file_path, "r") as f:
        content = f.read()
        install_json = json.loads(content)

        artifacts = install_json["artifacts"]
        deps = install_json["dependencies"]
        repository_key = list(install_json["repositories"].keys())[0]
        all_artifacts = install_json["repositories"][repository_key]

        conflict_resolution = _parse_conflict_resolution(install_json, mvn_install_name)

        for json_dep in all_artifacts:
            group_id_artifact_id = _normalize_dependency_string_to_group_id_artifact_id(json_dep)
            version = artifacts[group_id_artifact_id]["version"]
            coord = json_dep + ":" + version
            dep = dependency.new_dep_from_maven_art_str(coord, mvn_install_name)
            if dep in conflict_resolution:
                dep = conflict_resolution[dep]
            if dep.classifier != "sources":
                transitives = []
                transitives_to_process = []
                if group_id_artifact_id in deps:
                    for transitive_gav in deps[group_id_artifact_id]:
                        transitive_group_id_artifact_id = _normalize_dependency_string_to_group_id_artifact_id(transitive_gav)
                        version = artifacts[transitive_group_id_artifact_id]["version"]
                        transitive_gav = transitive_gav + ":" + version
                        transitive_dep = dependency.new_dep_from_maven_art_str(transitive_gav, mvn_install_name)
                        if transitive_dep in conflict_resolution:
                            transitive_dep = conflict_resolution[transitive_dep]
                        transitives.append(transitive_dep)
                        # We need to process the transitives dependencies too to get the full transitive closure.
                        transitives_to_process.append(transitive_gav)
                    # Process dependencies of transitives in the same way as we do above.
                    # This is done recursively so if we encounter a transitive that we haven't processed yet, append it to be processed.
                    for transitive_to_process in transitives_to_process:
                        transitive_group_id_artifact_id = _normalize_dependency_string_to_group_id_artifact_id(transitive_to_process)
                        if transitive_group_id_artifact_id in deps:
                            for transitive_gav in deps[transitive_group_id_artifact_id]:
                                transitive_group_id_artifact_id = _normalize_dependency_string_to_group_id_artifact_id(transitive_gav)
                                version = artifacts[transitive_group_id_artifact_id]["version"]
                                transitive_gav = transitive_gav + ":" + version
                                transitive_dep = dependency.new_dep_from_maven_art_str(transitive_gav, mvn_install_name)
                                if transitive_dep in conflict_resolution:
                                    transitive_dep = conflict_resolution[transitive_dep]
                                if transitive_dep not in transitives:
                                    transitives.append(transitive_dep)
                                if transitive_gav not in transitives_to_process:
                                    transitives_to_process.append(transitive_gav)
                exclusions = ()
                result.append((dep, transitives, exclusions))
    return result


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


def _parse_conflict_resolution(json_dep_tree, mvn_install_name):
    conflict_resolution = {}
    if "conflict_resolution" in json_dep_tree:
        # if there is a conflict_resolution attribute, we have to honor it
        # it maps actual gav -> gav used in rest of file, with the only diff
        # being the version.
        #
        # for example:
        # "conflict_resolution": {
        #    "com.sun.jersey:jersey-client:1.17-ext": "com.sun.jersey:jersey-client:1.17",
        #    "com.sun.jersey:jersey-core:1.17-ext": "com.sun.jersey:jersey-core:1.17"
        # },
        # above, the dep version we want is "1.17-ext", but rest of the pinned
        # file uses "1.17"
        #
        # we'll store this as a lookup the other way:
        # dep used in pinned file -> dep we actually want
        for gav_key, gav_value in json_dep_tree["conflict_resolution"].items():
            wanted_dep = dependency.new_dep_from_maven_art_str(gav_key, mvn_install_name)
            actual_dep = dependency.new_dep_from_maven_art_str(gav_value, mvn_install_name)
            assert actual_dep not in conflict_resolution
            conflict_resolution[actual_dep] = wanted_dep
    return conflict_resolution


def is_never_link_dep(repository_root_path, package):
    """
    Check if the dependency has neverlink set to 1
    java_library with neverlink set to 1 should not be considered because required only at compilation time
    Bazel ref: https://docs.bazel.build/versions/main/be/java.html#java_library.neverlink:~:text=on%20this%20target.-,neverlink,-Boolean%3B%20optional%3B%20default
    """
    query = "bazel query 'attr('neverlink', 1, %s)'" % package
    stdout = run_cmd(query, cwd=repository_root_path)
    return package in stdout

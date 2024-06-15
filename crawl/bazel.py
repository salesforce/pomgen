"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module has methods that return information about the monorepo structure.

Whenever possible, the code here delegates to "bazel query" to gather the
requested data.
"""

from common import logger
from common import mdfiles
from common.os_util import run_cmd
from common import logger
from collections import defaultdict
from crawl import dependency
import os
import json


def query_java_library_deps_attributes(repository_root_path, target_pattern,
                                       dep_attributes, verbose=False):
    """
    Returns, as a list of strings, the combined values of the dep_attributes
    given, typically 'deps' and 'runtime_deps', of the (java_library) rule
    identified by the specified target_pattern.

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

    query_parts = ["labels(%s, %s)" % (attr, target_pattern) for attr in dep_attributes]
    query = "bazel query --noimplicit_deps --order_output full '%s'" % " union ".join(query_parts)
    if verbose:
        logger.debug("Running query: %s" % query)
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


def parse_maven_install(names_and_paths, label_to_overridden_fq_label={}, verbose=False):
    """
    Parses the given maven_install pinned json files.

    Returns the parsed dependencies, as an iterable of tuples:
      - t[0]: a dependency.Dependency instance
      - t[1]: for the dependency at t[0], an iterable of the dependencies
              it references (the full transitive closure)
    """
    # internal bookkeeping: stores a mapping of unqualified label (without the
    # @maven_install_name prefix) to a list of deps with that unqualified label
    # the label is a str, the deps are _DepWithDirects instances
    # this is a one to many mapping because there may be multiple matching
    # deps, each in a different maven install rule
    unqual_label_to_deps = defaultdict(list)
    # internal bookkeeping: stores a mapping of qualified label (with the
    # @maven_install_name prefix) to the dep with that label
    # the label is a str, the dep is a _DepWithDirects instance
    fq_label_to_dep = {}

    # parse pinned files
    for name, pinned_file_path in names_and_paths:
        for dep in _parse_pinned(name, pinned_file_path, verbose):
            d = dep.dep # dep is a _DepWithDirects instance
            unqual_label_to_deps[d.unqualified_bazel_label_name].append(dep)
            assert d.bazel_label_name not in fq_label_to_dep
            fq_label_to_dep[d.bazel_label_name] = dep


    # process overrides (if there are any)
    # for each dep, we update the direct transitives with the overridden
    # dep(s)
    for unqual_label, fq_label in label_to_overridden_fq_label.items():
        src_deps = unqual_label_to_deps.get(unqual_label, [])
        for src_dep in src_deps:
            if fq_label in fq_label_to_dep:
                target_dep = fq_label_to_dep[fq_label]
                for dep in fq_label_to_dep.values():
                    for i, direct in enumerate(dep.directs):
                        if direct is src_dep:
                            dep.directs[i] = target_dep


    # final result: list of tuples: (dep, transitive closure of deps)
    # the deps are dependency.Dependency instances
    dep_and_transitives = []

    # compute transitive closure for each top level dep and assemble the result
    for dep in fq_label_to_dep.values():
        unwrapped_dep = dep.dep
        unwrapped_transitives = [t.dep for t in dep.get_transitive_closure()]
        dep_and_transitives.append((unwrapped_dep, unwrapped_transitives,))

    return dep_and_transitives


def _parse_pinned(mvn_install_name, pinned_file_path, verbose=False):
    """
    Parses the maven_install pinned json file with the given name (ns) and path.

    Returns an iterable of _DepWithDirects instances, one for each top level
    encountered in the pinned file.
    """
    if verbose:
        logger.debug("Processing pinned file [%s]" % pinned_file_path)
    result = []
    with open(pinned_file_path, "r") as f:
        content = f.read()
    install_json = json.loads(content)
    repository_key = list(install_json["repositories"].keys())[0]
    all_artifacts_json = install_json["repositories"][repository_key]
    artifacts_json = install_json["artifacts"]
    direct_deps_json = install_json["dependencies"]
    conflict_resolution = _parse_conflict_resolution(install_json, mvn_install_name)

    # collect top level dependencies and build a mappping of
    # coord -> dependency.Dependency instance
    # note that the coord doesn't have the version component, but the dep does
    # this is because the coord without version is a lookup key in the pinned
    # maven_install file
    coord_wo_vers_to_dep = {}
    for coord_wo_vers in all_artifacts_json:
        dep = dependency.new_dep_from_maven_art_str(
            coord_wo_vers + ":-1", mvn_install_name)
        # we need the group_id and artifact_id only to lookup the version
        group_id_artifact_id = "%s:%s" % (dep.group_id, dep.artifact_id)
        version = artifacts_json[group_id_artifact_id]["version"]
        dep = dependency.new_dep_from_maven_art_str(
            coord_wo_vers + ":" + version, mvn_install_name)
        if dep in conflict_resolution:
            dep = conflict_resolution[dep]
        if dep.classifier != "sources":
            assert coord_wo_vers not in coord_wo_vers_to_dep
            coord_wo_vers_to_dep[coord_wo_vers] = _DepWithDirects(dep)

    # for each top level dependency, find and associate direct transitives
    deps_with_directs = []
    for coord_wo_vers, dep in coord_wo_vers_to_dep.items():
        direct_dep_coords_wo_vers = direct_deps_json.get(coord_wo_vers, [])
        dep.directs = _get_direct_deps(direct_dep_coords_wo_vers,
                                       coord_wo_vers_to_dep, mvn_install_name,
                                       verbose, fail_on_missing=False)
        if len(dep.directs) == 0:
            # something failed. rerun but this time with more logging
            # and mark it to blow up when it hits the failure
            dep.directs = _get_direct_deps(direct_dep_coords_wo_vers,
                                           coord_wo_vers_to_dep,
                                           mvn_install_name, verbose=True,
                                           fail_on_missing=True)

    return coord_wo_vers_to_dep.values()


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


def _get_direct_deps(direct_dep_coords_wo_vers, coord_wo_vers_to_dep, maven_install_filename, verbose, fail_on_missing):
    direct_deps = []
    for direct_dep_coord_wo_vers in direct_dep_coords_wo_vers:
        direct_dep = None
        if direct_dep_coord_wo_vers in coord_wo_vers_to_dep:
            direct_dep = coord_wo_vers_to_dep[direct_dep_coord_wo_vers]
            if verbose:
                logger.debug("Found top level dep in [%s] as [%s]" %
                    (maven_install_filename, direct_dep_coord_wo_vers))
        else:
            alt_coords = _get_alt_lookup_coords(direct_dep_coord_wo_vers)
            for alt_direct_dep_coord_wo_vers in alt_coords:
                if alt_direct_dep_coord_wo_vers in coord_wo_vers_to_dep:
                    if verbose:
                        logger.debug("Found top level dep in [%s] using alt coord [%s] instead of [%s]" %
                            (maven_install_filename, alt_direct_dep_coord_wo_vers, direct_dep_coord_wo_vers))
                    direct_dep = coord_wo_vers_to_dep[alt_direct_dep_coord_wo_vers]
                    break

        if direct_dep is None:
            msg = "Failed to find top level dependency instance for [{0}] with direct dep coord [{1}]".format(
                maven_install_filename, direct_dep_coord_wo_vers)
            logger.warning(msg)
            assert not fail_on_missing, msg
            return []
        direct_deps.append(direct_dep)
    return direct_deps


def _get_alt_lookup_coords(coord_wo_vers):
    """
    Covers the following observed edge cases in pinned files:
      - the reference uses "test-jar" packaging and the top level
        dep has "jar" packaging with "tests" classifier.
    """
    alternate_coords = []
    dep = dependency.new_dep_from_maven_art_str(coord_wo_vers + ":-1", "unused")
    if dep.packaging == "test-jar":
        alternate_coords.append("%s:%s:jar:tests" % (dep.group_id, dep.artifact_id))
    return alternate_coords


def is_never_link_dep(repository_root_path, package):
    """
    Check if the dependency has neverlink set to 1
    java_library with neverlink set to 1 should not be considered because required only at compilation time
    Bazel ref: https://docs.bazel.build/versions/main/be/java.html#java_library.neverlink:~:text=on%20this%20target.-,neverlink,-Boolean%3B%20optional%3B%20default
    """
    query = "bazel query 'attr('neverlink', 1, %s)'" % package
    stdout = run_cmd(query, cwd=repository_root_path)
    return package in stdout


class _DepWithDirects:
    """
    Helper class to track a dep with its direct transitives.
    The rest of pomgen only cares about dep -> transives closure of its deps,
    but while processing pinned files, storing this intermediate state is
    useful.
    """
    def __init__(self, dep):
        self.dep = dep
        self.directs = []

    def get_transitive_closure(self):
        transitive_closure = []
        _DepWithDirects._collect_directs(self, transitive_closure)
        return transitive_closure

    @classmethod
    def _collect_directs(clazz, current_dep, all_deps):
        for d in current_dep.directs:
            if d not in all_deps:
                all_deps.append(d)
                _DepWithDirects._collect_directs(d, all_deps)

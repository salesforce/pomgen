"""
Copyright (c) 2025, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import collections
import common.logger as logger
import generate.impl.pom.dependency as dependency
import json


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
    unqual_label_to_deps = collections.defaultdict(list)
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
            if direct_dep_coord_wo_vers.endswith(":pom"):
                # this is an edge case where a dependency is a pom
                # ex: org.kie.modules:org-apache-commons-lang3:pom
                msg = "Direct dependency on a pom [{0}] in namespace [{1}] is ignored. Please depend on actual jar files instead.".format(
                    direct_dep_coord_wo_vers, maven_install_filename)
                logger.warning(msg)
            else:
                msg = "Failed to find top level dependency instance for [{0}] with direct dep coord [{1}]".format(
                    maven_install_filename, direct_dep_coord_wo_vers)
                logger.warning(msg)
                assert not fail_on_missing, msg
                return []
        else:
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

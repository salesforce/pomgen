"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Command line utility that shows information about artifacts.
"""


import argparse
import collections
import functools
import common.argsupport as argsupport
import common.common as common
import common.instancequery as instancequery
import common.logger as logger
import common.version_increment_strategy as vis
import config.config as config
import crawl.bazel as bazel
import crawl.crawler as crawler
import crawl.libaggregator as libaggregator
import common.manifestcontent as manifestcontent
import crawl.workspace as workspace
import generate.generationstrategyfactory as generationstrategyfactory
import packagemanager.nexus as nexus
import json
import os
import sys


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Query Maven artifact metadata")
    parser.add_argument("--package", type=str, required=False,
        help="Narrows queries to the specified package(s). " + argsupport.get_package_doc())

    parser.add_argument("--repo_root", type=str, required=False,
        help="the root of the repository")
    
    parser.add_argument("--list_libraries", action="store_true", required=False,
        help="Prints list of libraries under the specified package - output is json")

    parser.add_argument("--list_artifacts", action="store_true", required=False,
        help="Prints list of artifacts under the specified package - output is json")

    parser.add_argument("--list_external_dependencies", action="store_true", required=False,
        help="Prints list of all declared external dependencies, ignores the 'package' argument - output is json")

    parser.add_argument("--library_release_plan_tree", action="store_true",
                        required=False,
                        help="Prints release information about the libraries in the repository - output is human-readable")

    parser.add_argument("--library_release_plan_json", action="store_true",
                        required=False,
                        help="Prints release information about the libraries in the repository - output is json")

    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")

    parser.add_argument("--filter", type=str, required=False,
        help="Experimental support for further narrowing down results")

    parser.add_argument("--force", required=False, action="store_true",
        help="Simulates release information when --force option is used")

    parser.add_argument("--ensure_proposed_version_availability",
                        required=False, action="store_true",
        help="For each proposed release version, checks the package manager to ensure that artifacts with that version have not been published yet")

    return parser.parse_args(args)


def _to_json(thing):
    return json.dumps(thing, indent=2)


def _compute_proposed_next_versions(lib_node, all_artifact_defs, vers_incr_strat, nexus_artifact_url, verbose=False):
    """
    Computes the proposed release and development versions for the given
    library node. If nexus_artifact_url is not None, increments the release
    version until it is available in Nexus, by checking all artifacts in the
    library.
    """
    current_version = lib_node.md_version
    rel_vers = vers_incr_strat.get_next_release_version(current_version)
    if nexus_artifact_url is not None and lib_node.requires_release:
        lib_artifact_defs = [art_def for art_def in all_artifact_defs if art_def.library_path == lib_node.library_path]
        # TODO this assumes nexus - needs to instead pick the right package
        # managers based on the artifact type being processed
        rel_vers = nexus.get_next_available_version(
            lib_artifact_defs,
            rel_vers, nexus_artifact_url,
            vers_incr_strat,
            verbose)
    dev_vers = vers_incr_strat.get_next_development_version(rel_vers)
    return rel_vers, dev_vers


if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root, args.verbose)
    fac = generationstrategyfactory.GenerationStrategyFactory(
        repo_root, cfg, manifestcontent.NOOP, args.verbose)
    ws = workspace.Workspace(repo_root, cfg, fac)
    determine_packages_to_process = (args.list_libraries or 
                                     args.list_artifacts or
                                     args.library_release_plan_tree or
                                     args.library_release_plan_json)
    if determine_packages_to_process:
        if args.verbose:
            logger.debug("Starting with package [%s]" % args.package)
        packages = argsupport.get_all_packages(repo_root, args.package, fac, args.verbose)
        if args.verbose:
            logger.debug("Expanded initial package to %s" % packages)
        packages = ws.filter_artifact_producing_packages(packages)
        if args.verbose:
            logger.debug("Filtered packages down to %s" % packages)
        if len(packages) == 0:
            raise Exception("Did not find any BUILD.pom packages at [%s]" % args.package)

    if args.list_libraries:
        all_libs = []
        for lib_path in bazel.query_all_libraries(repo_root, packages, fac, args.verbose):
            attrs = collections.OrderedDict()
            attrs["name"] = os.path.basename(lib_path)
            attrs["path"] = lib_path
            all_libs.append(attrs)
        print(_to_json(all_libs))

    if args.list_artifacts:
        artifacts = [ws.parse_maven_artifact_def(p) for p in packages]
        if args.filter is not None:
            query = instancequery.InstanceQuery(args.filter)
            artifacts = query(artifacts)
        output = []
        for artifact in sorted(artifacts, key=lambda a: a.bazel_package):
            attrs = collections.OrderedDict()
            attrs["artifact_id"] = artifact.artifact_id
            if artifact.group_id is not None:
                attrs["group_id"] = artifact.group_id
            attrs["version"] = artifact.version
            attrs["path"] = artifact.bazel_package
            attrs["library_path"] = artifact.library_path
            output.append(attrs)
        print(_to_json(output))

    if args.list_external_dependencies:
        external_dependencies = sorted(fac.load_all_external_dependencies(), key=lambda dep: dep.label)
        ext_deps = []
        for external_dependency in external_dependencies:
            attrs = collections.OrderedDict()
            attrs["artifact_id"] = external_dependency.artifact_id
            attrs["group_id"] = external_dependency.group_id
            attrs["version"] = external_dependency.version
            attrs["packaging"] = external_dependency.packaging
            attrs["classifier"] = external_dependency.classifier
            attrs["name"] = external_dependency.label.canonical_form
            ext_deps.append(attrs)
        if args.filter is not None:
            # filter AFTER building result dict so that filtering on ancestors
            # is possible
            query = instancequery.InstanceQuery(args.filter)
            ext_deps = query(ext_deps)
        print(_to_json(ext_deps))

    crawl_artifact_dependencies = (args.library_release_plan_tree or
                                   args.library_release_plan_json)

    if args.ensure_proposed_version_availability:
        assert cfg.nexus_artifact_url is not None, "nexus_artifact_url must be configured in .poppyrc [artifact] section"

    if crawl_artifact_dependencies:
        crawler = crawler.Crawler(ws, args.verbose)
        crawler_result = crawler.crawl(packages, force_release=args.force)
        root_library_nodes = libaggregator.get_libraries_to_release(crawler_result.nodes)

        if args.library_release_plan_tree:
            pretty_tree_output = ""
            for library_node in root_library_nodes:
                pretty_tree_output = "%s\n%s\n" % (pretty_tree_output,
                                                   library_node.pretty_print())
            print(pretty_tree_output)

        else:
            if args.library_release_plan_json:
                all_libs_json = []
                all_artifact_defs = [ctx.artifact_def for ctx in crawler_result.artifact_generation_contexts]
                incremental_rel_enabled = cfg.transitives_versioning_mode == "counter"
                all_lib_nodes = sorted(libaggregator.LibraryNode.ALL_LIBRARY_NODES)
                for node in all_lib_nodes:
                    transitive = node not in root_library_nodes
                    increment_rel_qualifier = (
                        incremental_rel_enabled and
                        transitive and
                        len([p for p in cfg.always_semver_path_prefixes if node.library_path.startswith(p)]) == 0)
                    attrs = collections.OrderedDict()
                    attrs["library_path"] = node.library_path
                    attrs["version"] = node.version
                    attrs["released_version"] = node.released_version
                    attrs["requires_release"] = node.requires_release
                    attrs["release_reason"] = node.release_reason

                    next_release_version = None
                    next_dev_version = None
                    if node.version is None:
                        # edge case when the generation_mode is "skip"
                        version_incr_strat = None
                    else:
                        strat_name = None if increment_rel_qualifier else node.version_increment_strategy_name
                        version_incr_strat = vis.get_version_increment_strategy(
                            strat_name, node.md_version, node.released_version)
                    if version_incr_strat is not None:
                        nexus_url = None
                        if args.ensure_proposed_version_availability:
                            assert cfg.nexus_artifact_url is not None
                            nexus_url = cfg.nexus_artifact_url
                        next_rel_vers, next_dev_vers = \
                        _compute_proposed_next_versions(
                            node,
                            all_artifact_defs,
                            version_incr_strat,
                            nexus_url,
                            args.verbose)
                    attrs["proposed_release_version"] = next_rel_vers
                    attrs["proposed_next_dev_version"] = next_dev_vers

                    all_libs_json.append(attrs)
                print(_to_json(all_libs_json))

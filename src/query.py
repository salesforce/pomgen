"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Command line utility that shows information about Maven artifacts.
"""

from collections import OrderedDict
from common import argsupport
from common import common
from common import instancequery
from common import logger
from common import maveninstallinfo
from common import overridefileinfo
from common import version_increment_strategy as vis
from config import config
from crawl import bazel
from crawl import buildpom
from crawl import crawler
from crawl import dependencymd as dependencymdm
from crawl import libaggregator
from crawl import pomcontent
from crawl import workspace
from generate.impl import pomgenerationstrategy
import argparse
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
                        help="Prints release information about the libraries in the monorepo - output is human-readable")

    parser.add_argument("--library_release_plan_json", action="store_true",
                        required=False,
                        help="Prints release information about the libraries in the monorepo - output is json")

    parser.add_argument("--artifact_release_plan", action="store_true",
                        required=False,
                        help="Prints release information about the artifacts in the monorepo - output is json")

    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")

    parser.add_argument("--filter", type=str, required=False,
        help="Experimental support for further narrowing down results")

    parser.add_argument("--force", required=False, action="store_true",
        help="Simulates release information when --force option is used")

    return parser.parse_args(args)


def _get_version_increment_strategy(node, increment_rel_qualifier):
    if node.version is None:
        # edge case when uncommon (never used?) pom_generation_mode is "skip"
        return None
    if increment_rel_qualifier:
        return vis.get_rel_qualifier_increment_strategy(node.released_version)
    else:
        return vis.get_version_increment_strategy(node.version_increment_strategy_name)


def _to_json(thing):
    return json.dumps(thing, indent=2)


if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root, args.verbose)
    dep_overrides = overridefileinfo.OverrideFileInfo(
        cfg.override_file_paths, repo_root).label_to_overridden_fq_label
    mvn_install_info = maveninstallinfo.MavenInstallInfo(cfg.maven_install_paths)
    depmd = dependencymdm.DependencyMetadata(cfg.jar_artifact_classifier)    
    ws = workspace.Workspace(repo_root, cfg, mvn_install_info, pomcontent.NOOP,
                             dependency_metadata=depmd,
                             label_to_overridden_fq_label=dep_overrides,
                             verbose=args.verbose)

    determine_packages_to_process = (args.list_libraries or 
                                     args.list_artifacts or
                                     args.library_release_plan_tree or
                                     args.library_release_plan_json or
                                     args.artifact_release_plan)

    if determine_packages_to_process:
        if args.verbose:
            logger.debug("Starting with package [%s]" % args.package)
        packages = argsupport.get_all_packages(repo_root, args.package, args.verbose)
        if args.verbose:
            logger.debug("Expanded initial package to %s" % packages)
        packages = ws.filter_artifact_producing_packages(packages)
        if args.verbose:
            logger.debug("Filtered packages down to %s" % packages)
        if len(packages) == 0:
            raise Exception("Did not find any BUILD.pom packages at [%s]" % args.package)

    if args.list_libraries:
        all_libs = []
        for lib_path in bazel.query_all_libraries(repo_root, packages, args.verbose):
            attrs = OrderedDict()
            attrs["name"] = os.path.basename(lib_path)
            attrs["path"] = lib_path
            all_libs.append(attrs)
        print(_to_json(all_libs))

    if args.list_artifacts:
        maven_artifacts = [buildpom.parse_maven_artifact_def(repo_root, p) for p in packages]
        all_artifacts = []
        if args.filter is not None:
            query = instancequery.InstanceQuery(args.filter)
            maven_artifacts = query(maven_artifacts)
        for maven_artifact in sorted(maven_artifacts, key=lambda a: a.bazel_package):
            attrs = OrderedDict()
            attrs["artifact_id"] = maven_artifact.artifact_id
            attrs["group_id"] = maven_artifact.group_id
            attrs["version"] = maven_artifact.version
            attrs["path"] = maven_artifact.bazel_package
            all_artifacts.append(attrs)
        print(_to_json(all_artifacts))

    if args.list_external_dependencies:
        external_dependencies = sorted(ws.external_dependencies, key=lambda dep: dep.bazel_label_name)
        ext_deps = []
        for external_dependency in external_dependencies:
            attrs = OrderedDict()
            attrs["artifact_id"] = external_dependency.artifact_id
            attrs["group_id"] = external_dependency.group_id
            attrs["version"] = external_dependency.version
            attrs["classifier"] = external_dependency.classifier
            attrs["name"] = external_dependency.bazel_label_name
            ext_deps.append(attrs)
        if args.filter is not None:
            # filter AFTER building result dict so that filtering on ancestors
            # is possible
            query = instancequery.InstanceQuery(args.filter)
            ext_deps = query(ext_deps)
        print(_to_json(ext_deps))

    crawl_artifact_dependencies = (args.library_release_plan_tree or
                                   args.library_release_plan_json or
                                   args.artifact_release_plan)

    if crawl_artifact_dependencies:
        gen_strategy = pomgenerationstrategy.PomGenerationStrategy(ws, cfg.pom_template)
        crawler = crawler.Crawler(ws, gen_strategy, cfg.pom_template, args.verbose)
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
                incremental_rel_enabled = cfg.transitives_versioning_mode == "counter"
                for node in libaggregator.LibraryNode.ALL_LIBRARY_NODES:
                    transitive = node not in root_library_nodes
                    increment_rel_qualifier = incremental_rel_enabled and transitive
                    version_strat = _get_version_increment_strategy(
                        node, increment_rel_qualifier)
                    attrs = OrderedDict()
                    attrs["library_path"] = node.library_path
                    attrs["version"] = node.version
                    attrs["released_version"] = node.released_version
                    attrs["requires_release"] = node.requires_release
                    attrs["release_reason"] = node.release_reason

                    next_release_version = None
                    next_dev_version = None
                    if version_strat is not None:
                        next_release_version = version_strat.get_next_release_version(node.version)
                        next_dev_version = version_strat.get_next_development_version(node.version)
                    attrs["proposed_release_version"] = next_release_version
                    attrs["proposed_next_dev_version"] = next_dev_version

                    all_libs_json.append(attrs)
                print(_to_json(all_libs_json))
            
            if args.artifact_release_plan:
                all_artifacts_json = []
                for dep in crawler_result.crawled_bazel_packages:
                    attrs = OrderedDict()
                    attrs["artifact_id"] = dep.artifact_id
                    attrs["group_id"] = dep.group_id
                    attrs["version"] = dep.version
                    attrs["requires_release"] = not dep.external
                    attrs["bazel_label"] = "//%s" % dep.bazel_package if dep.bazel_buildable else None
                    all_artifacts_json.append(attrs)
                print(_to_json(all_artifacts_json))

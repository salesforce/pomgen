#!/usr/bin/env python

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Command line utility that shows information about libraries in the monorepo.
"""

from collections import OrderedDict
from common import argsupport
from common import common
from common import version
from config import config
from crawl import bazel
from crawl import buildpom
from crawl import crawler
from crawl import libaggregator
from crawl import workspace
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
    
    parser.add_argument("--list_libraries", action='store_true', required=False,
        help="Prints list of libraries under the specified package - output is json")

    parser.add_argument("--list_artifacts", action='store_true', required=False,
        help="Prints list of artifacts under the specified package - output is json")

    parser.add_argument("--list_all_external_dependencies", action='store_true', required=False,
        help="Prints list of all declared external dependencies, ignores the 'package' argument - output is json")

    parser.add_argument("--library_release_plan_tree", action='store_true',
                        required=False,
                        help="Prints release information about the libraries in the monorepo - output is human-readable")

    parser.add_argument("--library_release_plan_json", action='store_true',
                        required=False,
                        help="Prints release information about the libraries in the monorepo - output is json")

    parser.add_argument("--artifact_release_plan", action='store_true',
                        required=False,
                        help="Prints release information about the artifacts in the monorepo - output is json")

    parser.add_argument("--verbose", required=False, action='store_true',
        help="Verbose output")

    # this is experimental and not generalized yet
    parser.add_argument("--filter", type=str, required=False,
        help="Generic query filter, currently only supported for artifact queries")

    return parser.parse_args(args)

def _target_for_monorepo_dep(repo_root, dep):
    assert dep.bazel_package is not None
    # not all monorepo artifacts have valid bazel targets, some
    # are pom-only artifacts without BUILD file, so we check
    # for BUILD file presence here
    if os.path.exists(os.path.join(repo_root, dep.bazel_package, "BUILD")):
        return "//%s" % dep.bazel_package
    else:
        return None

def _to_json(thing):
    return json.dumps(thing, indent=2)

if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root)
    ws = workspace.Workspace(repo_root, cfg.external_dependencies, 
                             cfg.excluded_dependency_paths, 
                             cfg.all_src_exclusions)

    determine_packages_to_process = (args.list_libraries or 
                                     args.list_artifacts or
                                     args.library_release_plan_tree or
                                     args.library_release_plan_json or
                                     args.artifact_release_plan)

    if determine_packages_to_process:
        packages = argsupport.get_all_packages(repo_root, args.package)
        packages = ws.filter_artifact_producing_packages(packages)
        if len(packages) == 0:
            raise Exception("Did not find any BUILD.pom packages at [%s]" % args.package)

    if args.list_libraries:
        all_libs = []
        for lib_path in bazel.query_all_libraries(repo_root, packages):
            attrs = OrderedDict()
            attrs["name"] = os.path.basename(lib_path)
            attrs["path"] = lib_path
            all_libs.append(attrs)
        print(_to_json(all_libs))

    if args.list_artifacts:
        maven_artifacts = [buildpom.parse_maven_artifact_def(repo_root, p) for p in packages]
        all_artifacts = []
        for maven_artifact in maven_artifacts:
            if args.filter is not None:
                attr_filter_name, attr_filter_value = args.filter.split("=")
                if hasattr(maven_artifact, attr_filter_name):
                    value = getattr(maven_artifact, attr_filter_name)
                    if attr_filter_value != str(value):
                        continue
            attrs = OrderedDict()
            attrs["artifact_id"] = maven_artifact.artifact_id
            attrs["group_id"] = maven_artifact.group_id
            attrs["version"] = maven_artifact.version
            attrs["path"] = maven_artifact.bazel_package
            all_artifacts.append(attrs)
        print(_to_json(all_artifacts))

    if args.list_all_external_dependencies:
        external_dependencies = list(ws.name_to_external_dependencies.values())
        external_dependencies.sort()
        all_ext_deps = []
        for external_dependency in external_dependencies:
            attrs = OrderedDict()
            attrs["artifact_id"] = external_dependency.artifact_id
            attrs["group_id"] = external_dependency.group_id
            attrs["version"] = external_dependency.version
            attrs["classifier"] = external_dependency.classifier
            attrs["name"] = external_dependency.bazel_label_name
            all_ext_deps.append(attrs)
        print(_to_json(all_ext_deps))

    crawl_artifact_dependencies = (args.library_release_plan_tree or
                                   args.library_release_plan_json or
                                   args.artifact_release_plan)

    if crawl_artifact_dependencies:
        crawler = crawler.Crawler(ws, cfg.pom_template, args.verbose)
        artifact_result = crawler.crawl(packages)
        library_nodes = libaggregator.get_libraries_to_release(artifact_result.nodes)

        if args.library_release_plan_tree:
            pretty_tree_output = ""
            for library_node in library_nodes:
                pretty_tree_output = "%s\n%s\n" % (pretty_tree_output,
                                                   library_node.pretty_print())
            print(pretty_tree_output)

        else:
            if args.library_release_plan_json:
                all_libs_json = []
                for node in libaggregator.LibraryNode.ALL_LIBRARY_NODES:
                    attrs = OrderedDict()
                    attrs["library_path"] = node.library_path
                    attrs["version"] = node.version
                    attrs["requires_release"] = node.requires_release
                    attrs["release_reason"] = node.release_reason
                    attrs["proposed_release_version"] = version.get_release_version(node.version)
                    attrs["proposed_next_dev_version"] = version.get_next_dev_version(node.version, node.version_increment_strategy)
                    all_libs_json.append(attrs)
                print(_to_json(all_libs_json))
            
            if args.artifact_release_plan:
                all_artifacts_json = []
                for dep in artifact_result.crawled_bazel_packages:
                    attrs = OrderedDict()
                    attrs["artifact_id"] = dep.artifact_id
                    attrs["group_id"] = dep.group_id
                    attrs["version"] = dep.version
                    attrs["requires_release"] = not dep.external
                    attrs["bazel_target"] = _target_for_monorepo_dep(repo_root, dep)
                    all_artifacts_json.append(attrs)
                print(_to_json(all_artifacts_json))

#!/usr/bin/env python

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

Generates a single pom to stdout that has <dependency/> entries for 3rd party
dependencies.
"""

from common import common
from common import maveninstallinfo
from config import config
from crawl import buildpom
from crawl import dependency
from crawl import dependencymd as dependencymdm
from crawl import pom
from crawl import pomcontent
from crawl import workspace
import argparse
import os
import sys


IGNORED_DEPENDENCY_PREFIXES = ("@bazel_tools",
                               "@local_config",
                               "@local_jdk",
                               "@remote_coverage_tools",
                               "@remote_java_tools",
                              )


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Third Party Pom Generator. This script generates a single pom file to stdout, containing 3rdparty dependencies. Dependencies are de-duped and sorted alphabetically by their group and artifact ids. If given no input, this script processes all declared 3rd party dependencies.")
    parser.add_argument("--repo_root", type=str, required=False,
        help="optional - the root of the repository")
    parser.add_argument("--stdin", required=False, action='store_true',
        help="optional - reads dependencies from stdin - this is useful to chain bazel query command(s), as input to this script. In this mode, this script will look for dependencies of the form \"@<maven_install_name>//:<dep>\" (the same syntax that is used in BUILD files), one on each line. Some special dependencies (for example @remote), are ignored.")
    parser.add_argument("--group_id", type=str, required=False,
        help="optional - the groupId to use in the generated pom")
    parser.add_argument("--artifact_id", type=str, required=False,
        help="optional - the artifactId to use in the generated pom")
    parser.add_argument("--version", type=str, required=False,
        help="optional - the version to use in the generated pom")
    parser.add_argument("--exclude_all_transitives", action="store_true",
                        required=False,
        help="optional - adds a *:* <exclusion> to all dependencies in the generated pom")

    return parser.parse_args(args)


class ThirdPartyDepsPomGen(pom.DynamicPomGen):
    def __init__(self, workspace, artifact_def, dependencies, pom_template):
        super(ThirdPartyDepsPomGen, self).__init__(workspace, artifact_def,
                                                   dependency=None,
                                                   pom_template=pom_template)
        self.dependencies = dependencies

    def _load_additional_dependencies_hook(self):
        return self.dependencies


def _starts_with_ignored_prefix(line):
    for prefix in IGNORED_DEPENDENCY_PREFIXES:
        if line.startswith(prefix):
            return True
    return False

def main(args):
    args = _parse_arguments(args)
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root)

    # For the primary function of pomgen (generating pom.xml files for publishing)
    # there are sometimes maven_install namespaces that are ignored in .pomgenrc.
    # These are identified as maven_install paths that begin with - .
    # For extdeps, we need to have full access to all maven_install namespaces, so
    # we tell maveninstallinfo to not honor the excludes.
    allow_excludes = False

    mvn_install_info = maveninstallinfo.MavenInstallInfo(cfg.maven_install_paths, allow_excludes)

    depmd = dependencymdm.DependencyMetadata(cfg.jar_artifact_classifier)
    ws = workspace.Workspace(repo_root, cfg, mvn_install_info,
                             pomcontent.NOOP, dependency_metadata=depmd,
                             label_to_overridden_fq_label={})

    group_id = "all_ext_deps_group" if args.group_id is None else args.group_id
    artifact_id = "all_ext_deps_art" if args.artifact_id is None else args.artifact_id
    version = "0.0.1-SNAPSHOT" if args.version is None else args.version

    artifact_def = buildpom.MavenArtifactDef(group_id=group_id,
                                             artifact_id=artifact_id,
                                             version=version)

    if args.stdin:
        dep_labels = set() # we want to de-dupe labels
        dependencies = []
        for line in sys.stdin:
            line = line.strip()
            if len(line) == 0:
                continue
            if not line.startswith("@"):
                continue
            if _starts_with_ignored_prefix(line):
                continue
            dep_labels.add(line)
        dependencies = ws.parse_dep_labels(dep_labels)
    else:
        dependencies = list(ws.external_dependencies)

    # to be nice:
    dependencies.sort()

    if args.exclude_all_transitives:
        # since all dependencies are treated equally (no transitives),
        # we can dedupe them without losing anything
        # we use a representation that includes the version when checking
        # whether we have already included the dep
        deps_set = set()
        updated_dependencies = []
        for dep in dependencies:
            dedupe_key = dep.maven_coordinates_name + ":" + dep.version
            if dedupe_key not in deps_set:
                deps_set.add(dedupe_key)
                updated_dependencies.append(dep)
        dependencies = updated_dependencies

        # ignore what was specified in the pinned dependencies files and instead
        # exclude all transitives: add an "exclude all dependency"
        # (* exclusions) for all dependencies that end up in the generated pom
        ws.dependency_metadata.clear()
        for dep in dependencies:
            ws.dependency_metadata.register_exclusions(
                dep, [dependency.EXCLUDE_ALL_PLACEHOLDER_DEP])
    else:
        # it is possible to end up with duplicate dependencies
        # because different labels may point to the same dependency (gav)
        # (for ex: @maven//:org_antlr_ST4 and @antlr//:org_antlr_ST4)
        pass

    pomgen = ThirdPartyDepsPomGen(ws, artifact_def, dependencies,
                                  cfg.pom_template)
    pomgen.process_dependencies()
    return pomgen.gen(pom.PomContentType.RELEASE)


if __name__ == "__main__":
    print(main(sys.argv[1:]))

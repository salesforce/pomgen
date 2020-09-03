#!/usr/bin/env python

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

Generates a single pom, to stdout, that has <dependency/> entries for every
declared 3rd party dependency.
"""

from common import common
from config import config
from crawl import buildpom
from crawl import pom
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
        help="optional - reads dependencies from stdin - this is useful to chain bazel query command(s), as input to this script. In this mode, this script will look for dependencies of the form \"@<name>//jar\", one on each line. Some special dependencies (for example @remote), are ignored.")
    parser.add_argument("--group_id", type=str, required=False,
        help="optional - the groupId to use in the generated pom")
    parser.add_argument("--artifact_id", type=str, required=False,
        help="optional - the artifactId to use in the generated pom")
    parser.add_argument("--version", type=str, required=False,
        help="optional - the version to use in the generated pom")

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
    ws = workspace.Workspace(repo_root, 
                             cfg.excluded_dependency_paths,
                             cfg.all_src_exclusions,
                             cfg.maven_install_rule_names)

    group_id = "all_ext_deps_group" if args.group_id is None else args.group_id
    artifact_id = "all_ext_deps_art" if args.artifact_id is None else args.artifact_id
    version = "0.0.1-SNAPSHOT" if args.version is None else args.version
    
    artifact_def = buildpom.MavenArtifactDef(group_id=group_id,
                                             artifact_id=artifact_id,
                                             version=version)

    if args.stdin:
        dep_labels = []
        dependencies = []
        for line in sys.stdin:
            line = line.strip()
            if len(line) == 0:
                continue
            if not line.startswith("@"):
                continue
            if _starts_with_ignored_prefix(line):
                continue
            dep_labels.append(line)
        unique_dependencies = set(ws.parse_dep_labels(dep_labels))
        dependencies = list(unique_dependencies)
    else:
        dependencies = list(ws.name_to_external_dependencies.values())

    dependencies.sort()
    pomgen = ThirdPartyDepsPomGen(ws, artifact_def, dependencies,
                                  cfg.pom_template)
    pomgen.process_dependencies()
    return pomgen.gen()

if __name__ == "__main__":
    print(main(sys.argv[1:]))

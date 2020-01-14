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

def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="3rdparty Pom Generator")
    parser.add_argument("--repo_root", type=str, required=False,
        help="the root of the repository")
    return parser.parse_args(args)

class ThirdPartyDepsPomGen(pom.DynamicPomGen):
    def __init__(self, workspace, artifact_def, dependencies, pom_template):
        super(ThirdPartyDepsPomGen, self).__init__(workspace, artifact_def, pom_template)
        self.dependencies = dependencies

    def _load_additional_dependencies_hook(self):
        return self.dependencies

if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)    
    cfg = config.load(repo_root)
    workspace = workspace.Workspace(repo_root, 
                                    cfg.external_dependencies, 
                                    cfg.excluded_dependency_paths,
                                    cfg.all_src_exclusions)
    
    artifact_def = buildpom.MavenArtifactDef(group_id="all_ext_deps_group",
                                             artifact_id="all_ext_deps_art",
                                             version="0.0.1-SNAPSHOT")

    all_dependencies = list(workspace.name_to_external_dependencies.values())
    all_dependencies.sort()
    pomgen = ThirdPartyDepsPomGen(workspace, artifact_def, all_dependencies, cfg.pom_template)
    pomgen.process_dependencies()
    print(pomgen.gen())

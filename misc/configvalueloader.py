"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Loads pomgen configuration values. Uses the syntax:
<section>.<config-key-name>
"""

import argparse
import sys
from common import common
from config import config as configm


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Configuration Value Loader")
    parser.add_argument("--key", type=str, required=True,
        help="The config key for which to load the value, must be prefixed with the config section name")
    parser.add_argument("--default", type=str, required=False,
        help="The default value to use if no configured value exists")
    parser.add_argument("--repo_root", type=str, required=False,
        help="The root of the repository")
    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")
    return parser.parse_args(args)
    

if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    cfg = configm.load(repo_root, args.verbose)
    # this isn't implemented for all config values yet ...
    if args.key == "artifact.jar_classifier":
        value = cfg.jar_artifact_classifier
    else:
        sys.exit("Unknown config key [%s], fix me if needed!" % args.key)
    if value is None:
        value = args.default
    print(value)

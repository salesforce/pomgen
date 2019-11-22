"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Common utility functions shared between command line entrypoints.
"""

import os

def get_repo_root(repo_root=None):
    if repo_root is None:
        repo_root = os.getcwd()

    if not os.path.exists(os.path.join(repo_root, "WORKSPACE")):
        raise Exception("repository root is not set correctly : [%s]" % repo_root)

    return repo_root


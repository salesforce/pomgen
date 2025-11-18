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

    if not _has_workspace_file(repo_root):
        # try again - https://github.com/bazelbuild/bazel/issues/3325
        env_var_name = "BUILD_WORKING_DIRECTORY"
        if env_var_name in os.environ:
            repo_root = os.environ[env_var_name]

    if not _has_workspace_file(repo_root):        
        raise Exception("repository root is not set correctly : [%s]" % repo_root)
    return repo_root


def read_file(path, must_exist=True):
    if not must_exist and not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)


def _has_workspace_file(repo_root):
    return os.path.exists(os.path.join(repo_root, "WORKSPACE"))


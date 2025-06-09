"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is the single source of truth for computing the location
of the various metadata files pomgen reads and writes.

It also has methods to read and write those metadata files.
"""

import os


LIB_ROOT_FILE_NAME = "LIBRARY.root"
JAR_LOCATION_HINT_FILE = "pomgen_jar_location_hint"


def is_library_package(md_path):
    """
    Returns True if the specified md package is a Maven Library root package.

    Note that the path MUST include the md directory, for example:
    path/to/root/projects/libs/foolib/WEB-INF.
    """
    if not os.path.isabs(md_path):
        raise Exception("md_path must be absolute: %s" % md_path)
    lib_file_path = _build_metadata_file_path(md_path, 
                                              package_path="", 
                                              file_name=LIB_ROOT_FILE_NAME)
    return os.path.exists(lib_file_path)


def read_file(root_path, package_path, file_path, must_exist=False):
    """
    Constructs a path from the specified arguments and reads the file at that
    path.

    Returns the file content, or None if the file does not exist or if the path
    does not point to a file.
    Also returns the full path of the metadata file.
    Content and path are returned as a tuple: (content, path)
    """
    path = _build_metadata_file_path(root_path, package_path, file_path)
    if not os.path.exists(path):
        assert not must_exist, "cannot read file, it doesn't exist at path [%s]" % path
        return (None, path)
    with open(path, "r") as f:
        return (f.read().strip(), path)


def write_file(content, root_path, package_path, md_file_name):
    """
    Constructs a path from the specified arguments and writes the specied
    content to the file at that path.

    The root_path + package_path must point to a valid directory.

    Returns the path the file was written to, which can be used for logging.
    """
    _validate_paths(root_path, package_path)

    path = _build_metadata_file_path(root_path, package_path, md_file_name)
    with open(path, "w") as f:
        f.write(content)
    return path



def get_package_relative_metadata_directory_paths():
    """
    Returns a list of relative paths, relative to the package root, that are
    paths to pomgen metadata directories.
    """
    # 100% leaky abstraction - should use generation strategy
    return ("MVN-INF", "md")


def _build_metadata_file_path(root_path, package_path, file_name):
    path = os.path.join(root_path, package_path, file_name)
    return path


def _validate_paths(root_path, package_path):
    if not os.path.isabs(root_path):
        raise Exception("root_path must be absolute: %s" % root_path)
    if os.path.isabs(package_path):
        raise Exception("package_path must not be absolute: %s" % package_path)
    abs_package_path = os.path.join(root_path, package_path)
    if not os.path.exists(abs_package_path):
        raise Exception("expected bazel package path to exist: %s" % abs_package_path)
    if not os.path.isdir(abs_package_path):
        raise Exception("expected bazel package path to be a directory: %s" % abs_package_path)


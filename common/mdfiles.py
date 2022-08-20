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


BUILD_POM_FILE_NAME = "BUILD.pom"
BUILD_POM_RELEASED_FILE_NAME = "BUILD.pom.released"
LIB_ROOT_FILE_NAME = "LIBRARY.root"
POM_XML_RELEASED_FILE_NAME = "pom.xml.released"
JAR_LOCATION_HINT_FILE = "pomgen_jar_location_hint"


_ALL_MD_FILE_NAMES = [
    BUILD_POM_FILE_NAME,
    BUILD_POM_RELEASED_FILE_NAME,
    LIB_ROOT_FILE_NAME,
    POM_XML_RELEASED_FILE_NAME,
]


# relative to bazel package dir
MD_DIR_NAME = "MVN-INF"


def is_library_package(abs_package_path):
    """
    Returns True if the specified package is a Maven Library root package.
    """
    if not os.path.isabs(abs_package_path):
        raise Exception("abs_package_path must be absolute: %s" % abs_package_path)
    lib_file_path = _build_metadata_file_path(abs_package_path, 
                                              package_path="", 
                                              file_name=LIB_ROOT_FILE_NAME)
    return os.path.exists(lib_file_path)


def is_artifact_package(abs_package_path):
    """
    Returns True if the specified package is a Maven Artifact package.
    """
    if not os.path.isabs(abs_package_path):
        raise Exception("abs_package_path must be absolute: %s" % abs_package_path)

    build_pom_file_path = _build_metadata_file_path(abs_package_path, 
                                                    package_path="", 
                                                    file_name=BUILD_POM_FILE_NAME)
    return os.path.exists(build_pom_file_path)


def read_file(root_path, package_path, md_file_name):
    """
    Constructs a path from the specified arguments and reads the file at the
    location the path points to.

    Returns the file content, or None if the file does not exist or if the path
    does not point to a file.
    Also returns the full path of the metadata file.
    Content and path are returned as a tuple: (content, path)
    """
    path = os.path.join(root_path, package_path)
    if not _file_exists(path, md_file_name):
        return (None, None)
    path = _build_metadata_file_path(root_path, package_path, md_file_name)
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

    abs_md_dir_path = os.path.join(root_path, package_path, MD_DIR_NAME)
    if not os.path.exists(abs_md_dir_path):
        os.mkdir(abs_md_dir_path)
    
    path = os.path.join(abs_md_dir_path, md_file_name)
    with open(path, "w") as f:
        f.write(content)

    return path


def move_files(root_path, packages, src_md_dir_name, dest_md_dir_name):
    """
    Moves metadata files to a new location for each specified package.
    """
    for package in packages:
        _move_files_for_package(root_path, package, src_md_dir_name, dest_md_dir_name)


def get_package_relative_metadata_directory_paths():
    """
    Returns a list of relative paths, relative to the package root, that are
    paths to pomgen metadata directories.
    """
    return () if len(MD_DIR_NAME) == 0 else (MD_DIR_NAME,)


def get_package_relative_metadata_file_paths():
    """
    Returns a list of relative paths, relative to the package root, that are
    paths to pomgen metadata files.
    """
    return _ALL_MD_FILE_NAMES if len(MD_DIR_NAME) == 0 else ()


def _move_files_for_package(root_path, package_path, src_md_dir_name, dest_md_dir_name):
    src_dir_path = os.path.join(root_path, package_path, src_md_dir_name)
    dest_dir_path = os.path.join(root_path, package_path, dest_md_dir_name)
    if os.path.exists(src_dir_path):
        for file_name in os.listdir(src_dir_path):
            # add pom.template to the list here, as that file may exist
            # and should also move, although it isn't considered a "core"
            # pomgen metadata file
            all_md_file_names = _ALL_MD_FILE_NAMES + ["pom.template"]
            if file_name in all_md_file_names:
                src_file_path = os.path.join(src_dir_path, file_name)
                if os.path.exists(src_file_path):
                    if not os.path.exists(dest_dir_path):
                        os.makedirs(dest_dir_path)
                    dest_file_path = os.path.join(dest_dir_path, file_name)
                    os.rename(src_file_path, dest_file_path)


def _build_metadata_file_path(root_path, package_path, file_name):
    return os.path.join(root_path, package_path, MD_DIR_NAME, file_name)


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


def _file_exists(abs_package_path, md_file_name):
    """
    Verifies whether the specified metadata_file_name file exists
    at the given package, specified as an absolute path.
    """
    if not os.path.isabs(abs_package_path):
        raise Exception("abs_package_path must be absolute: %s" % abs_package_path)
    file_path = _build_metadata_file_path(abs_package_path, 
                                          package_path="", 
                                          file_name=md_file_name)
    if not os.path.exists(file_path):
        return False
    if not os.path.isfile(file_path):
        return False
    return True


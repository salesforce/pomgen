"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import mdfiles
from common.os_util import run_cmd
import os
import tempfile

def get_dir_hash(repo_root_path, rel_path, source_exclusions):
    files_output = _ls_files(repo_root_path, rel_path, source_exclusions)
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(files_output)
        f.flush()
        output = run_cmd("git hash-object %s" % f.name, cwd=repo_root_path).strip()
        return output

def _ls_files(repo_root_path, rel_path, source_exclusions):
    excluded_rel_paths = [os.path.join(rel_path, excluded_relpath) for excluded_relpath in source_exclusions.relative_paths]

     # also ignore all directories containing metadata files
    excluded_rel_paths += [os.path.join(rel_path, f) for f in mdfiles.get_package_relative_metadata_directory_paths()]

    # these paths are ignored
    #   BUILD: a type of metadata file as far as pomgen is concerned
    excluded_rel_path_files = [os.path.join(rel_path, f) for f in ["BUILD",]]
    excluded_rel_path_files += [os.path.join(rel_path, f) for f in mdfiles.get_package_relative_metadata_file_paths()]

    # special case for exluding nested pomgen metadata (MVN-INF) directories.
    # this is to avoid the edge case that updating metadata in a inner bazel
    # package would cause the outer package to be marked as modified
    excluded_path_components = []
    for d in mdfiles.get_package_relative_metadata_directory_paths():
        if not d.startswith(os.sep):
            d = os.sep + d
        if not d.endswith(os.sep):
            d = d + os.sep
        excluded_path_components.append(d)

    output = run_cmd("git ls-files -s %s" % rel_path, cwd=repo_root_path).splitlines()
    filtered_output = []
    for line in output:
        # each line looks like this:
        # 100644 bc5732288be1c13d459f99d5fc9fc42da409fed8 0	path/from/root/of/repo/to/File.java
        file_rel_path = line[line.index(rel_path):].strip()
        include_file = True
        for excluded_rel_path in excluded_rel_paths:
            if file_rel_path.startswith(excluded_rel_path):
                include_file = False
                break

        for excluded_path_component in excluded_path_components:
            if excluded_path_component in file_rel_path:
                include_file = False
                break

        if include_file:
            if file_rel_path in excluded_rel_path_files:
                include_file = False

        if include_file:
            for excluded_file_name in source_exclusions.file_names:
                if os.path.basename(file_rel_path) == excluded_file_name:
                    include_file = False
                    break

        if include_file:
            for excluded_file_extension in source_exclusions.file_extensions:
                if file_rel_path.endswith(excluded_file_extension):
                    include_file = False
                    break

        if include_file:
            filtered_output.append(line)

    filtered_output.sort()

    return "\n".join(filtered_output)

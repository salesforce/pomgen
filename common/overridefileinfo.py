"""
Copyright (c) 2020, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import glob
import os


class OverrideFileInfo:

    def __init__(self, override_file_paths):
        self.override_file_paths = override_file_paths

    def get_override_file_names_and_paths(self, repository_root):
        """
        Returns a list of tuples (override file name, override file path)
        """
        names_and_paths = []
        for rel_path in self.override_file_paths:
            path = os.path.join(repository_root, rel_path)
            name_and_path = self._process_path(path)
            if name_and_path is None:
                globbed_names_and_paths = []
                if "*" in path:
                    for path in glob.glob(path):
                        name_and_path = self._process_path(path)
                        if name_and_path is not None:
                            globbed_names_and_paths.append(name_and_path)
                    names_and_paths += sorted(globbed_names_and_paths)
                else:
                    raise Exception("override file path not found [%s]" % path)
            else:
                names_and_paths.append(name_and_path)
        return names_and_paths

    def _process_path(self, path):
        """
        Returns a tuple (override file name, override file path) or None
        if the specified path is invalid.
        """
        override_file_suffix = ".bzl"
        if os.path.exists(path):
            fname = os.path.basename(path)
            if fname.endswith(override_file_suffix):
                return (fname[:-len(override_file_suffix)], path)
        return None


NOOP = OverrideFileInfo(())

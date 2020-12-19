"""
Copyright (c) 2020, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import glob
import os


class MavenInstallInfo:

    def __init__(self, maven_install_paths):
        self.maven_install_paths = maven_install_paths

    def get_maven_install_names_and_paths(self, repository_root):
        """
        Returns a list of tuples (mvn install name, mvn install path)
        """
        names_and_paths = []
        for rel_path in self.maven_install_paths:
            path = os.path.join(repository_root, rel_path)
            name_and_path = self._process_path(path)
            if name_and_path is None:
                globbed_names_and_paths = []
                if "*" in path:
                    for path in glob.glob(path):
                        name_and_path = self._process_path(path)
                        if name_and_path is not None:
                            globbed_names_and_paths.append(name_and_path)
                    # sort for predictable traversal order for tests
                    names_and_paths += sorted(globbed_names_and_paths)
            else:
                names_and_paths.append(name_and_path)
        return names_and_paths

    def _process_path(self, path):
        """
        Returns a tuple (mvn install name, mvn install path) or None
        if the specified path is invalid.
        """
        mvn_install_suffix = "_install.json"
        if os.path.exists(path):
            fname = os.path.basename(path)
            if fname.endswith(mvn_install_suffix):
                return (fname[:-len(mvn_install_suffix)], path)
        return None


NOOP = MavenInstallInfo(())

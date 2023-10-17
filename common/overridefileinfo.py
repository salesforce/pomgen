"""
Copyright (c) 2020, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import glob
import os
import re
import json


class OverrideFileInfo:

    def __init__(self, override_file_paths, repo_root_path):
        self.override_file_paths = override_file_paths
        self.repo_root_path = repo_root_path

    def overidden_dep_value(self, dep):
        overrides_dict = self.name_to_override_dependencies()
        if overrides_dict == {}:
            return dep
        if dep.override_key in overrides_dict.keys():
            return overrides_dict[dep.override_key]
        else:
            return dep

    def override_deps(self, deps, ext_deps):
        overrides_dict = self.name_to_override_dependencies()
        if overrides_dict == {}:
            return deps
        output_deps = []
        if overrides_dict == {}:
            return deps
        for dep in deps:
            overridded_str_dep = dep.override_key
            if overridded_str_dep in overrides_dict.keys() and overrides_dict[overridded_str_dep] in ext_deps.keys():
                dep = ext_deps[overrides_dict[overridded_str_dep]]
            output_deps.append(dep)
        return output_deps

    def name_to_override_dependencies(self):
        """
        Returns a dict for all overrides dependencies

        The mapping is of the form: {dep: overridded_dep}
        """
        override_file_names_and_paths = self.get_override_file_names_and_paths()
        if override_file_names_and_paths == 0:
            return {}
        overrides_dict = {}
        for (_, fpath) in override_file_names_and_paths:
            parsed_data = self._parse_override_file(fpath)
            overrides_dict.update(parsed_data)
        return overrides_dict

    def get_override_file_names_and_paths(self):
        """
        Returns a list of tuples (override file name, override file path)
        """
        names_and_paths = []
        for rel_path in self.override_file_paths:
            path = os.path.join(self.repo_root_path, rel_path)
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

    def _parse_override_file(self, file_path):
      """
      Returns a dict of {dep: overridded_dep} mapping
      """
      with open(file_path, "r") as f:
          contents = f.read()

          # Removes comments
          contents = re.sub("#.*\n", "", contents).split("{")[1].split("}")[0]

          # Removes whitespaces
          contents = re.sub(r'":\s+', '":', contents)
          contents = re.sub(r',\s+', ',', contents)

          # Removes the extra comma if present
          if contents.endswith(","):
              contents = contents[:-1]
          contents = "{" + contents.strip() + "}"
          override_data = json.loads(contents)
          output = {}

          # Updates /, . and - with _
          # Example - org.springframework:spring-jcl to org_springframework_spring_jcl
          for dep, overridded_dep in override_data.items():
              pattern = r'(?<=[^\d])\.|\.(?=[^\d])'
              output[re.sub(pattern, "_", dep.replace(':', '_').replace("-", "_"))] = overridded_dep
          return output

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


NOOP = OverrideFileInfo((), "")

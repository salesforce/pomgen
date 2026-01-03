import generate.impl.py.pydependency as pydependency


class RequirementsParser:
    """
    Requirements lock file parser.
    """
    def parse_requirements_lock_file(self, content):
        """
        Parses the requirements lock file content into a list of PyDependency
        instances. Ignores hash information and comments.
        
        Args:
            content: Content of a requirements lock file
            
        Returns:
            List of PyDependency instances.
        """
        return self._parse_dependencies(content)

    def _parse_dependencies(self, content):
        # return values:
        dependencies = []  # list of Dependeny instances to preserve order
        name_to_dependency = {}  # dict of dependency name -> PyDependency inst
        name_to_vias = {}  # dict of dependency name -> list of via values

        for line in content.splitlines():
            line = line.strip()
            if len(line) == 0:
                pass
            elif line.startswith("--"):
                pass
            elif line.startswith("#"):
                pass
            else:
                version_sep = "==" # we should support other comparison binops?
                version_sep_index = line.index(version_sep)
                name = line[0:version_sep_index]
                extras = ()
                if name.endswith("]"):
                    extras_start_index = name.index("[")
                    extras = name[extras_start_index+1:-1].split(",")
                    name = name[:extras_start_index]
                space_index = line.find(" ", version_sep_index)
                version = line[version_sep_index + len(version_sep):space_index]
                dependency = pydependency.PyDependency(name, version, extras=extras)
                dependencies.append(dependency)
        return dependencies

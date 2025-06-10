from .dependency import Dependency


class RequirementsParser:
    """
    Requirements lock file parser.
    """
    def parse_requirements_lock_file(self, content):
        """
        Parse requirements lock file content into a list of Dependency
        instances. Ignores hash information and comments.
        
        Args:
            content: Content of a requirements lock file
            
        Returns:
            List of Dependency instances representing top-level dependencies
        """
        dependencies, name_to_dependency, name_to_vias = self._parse_dependencies_and_vias(content)
        self._attach_dependencies(name_to_dependency, name_to_vias)
        return dependencies

    def _parse_dependencies_and_vias(self, content):
        # return values:
        dependencies = []  # list of Dependeny instances to preserve order
        name_to_dependency = {}  # dict of dependency name -> Dependency inst
        name_to_vias = {}  # dict of dependency name -> list of via values

        current_vias = None
        for line in content.splitlines():
            line = line.strip()
            if len(line) == 0:
                pass
            elif line.startswith("--"):
                pass
            elif line.startswith("#"):
                line = line[1:].strip()
                if line.startswith("via"):
                    assert current_vias is None
                    current_vias = []
                    line = line[3:].strip()
                    if len(line) > 0:
                        if line.startswith("-r "):
                            # via -r path/to/requirements.in
                            # directly referenced in requirements, no via
                            pass
                        else:
                            current_vias.append(line)
                else:
                    if current_vias is None:
                        pass
                    else:
                        if line.startswith("-r "):
                            # via -r path/to/requirements.in
                            # directly referenced in requirements, no via
                            pass
                        elif line.startswith("The following"):
                            # TODO: instead check "via" value has not space
                            pass
                        else:
                            current_vias.append(line)
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
                dependency = Dependency(name, version, extras=extras)
                dependencies.append(dependency)
                assert name not in name_to_dependency
                name_to_dependency[name] = dependency
                assert name not in name_to_vias
                # current_vias is None if there is no # via comment at all
                name_to_vias[name] = () if current_vias is None else current_vias
                current_vias = None
        return dependencies, name_to_dependency, name_to_vias

    def _attach_dependencies(self, name_to_dependency, name_to_vias):
        """Attach dependencies based on via relationships."""
        for name, vias in name_to_vias.items():
            child_dependency = name_to_dependency[name]
            for via in vias:
                parent_dependency = name_to_dependency[via]
                parent_dependency.child_dependencies.append(child_dependency)


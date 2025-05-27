class Dependency:
    """
    Represents a Python package dependency.
    """

    def __init__(self, name, version, extras=None):
        self.name = name
        self.version = version
        self.extras = tuple(extras) if extras else ()

        self.child_dependencies = []

    def to_pyproject_format(self):
        """Convert the dependency to pyproject.toml format."""
        if self.extras:
            # Format as TOML table with extras
            extras_str = ', '.join(f'"{extra}"' for extra in self.extras)
            return f'{{ version = "{self.version}", extras = [{extras_str}] }}'
        else:
            # Simple version string for packages without extras
            return f'"{self.version}"'

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return False
        return (self.name == other.name and 
                self.version == other.version and
                self.extras == other.extras)

    def __hash__(self):
        return hash((self.name, self.version, self.extras))

    def __str__(self):
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{self.name}{extras_str}{self.version}"

    def __repr__(self):
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"Dependency(name='{self.name}{extras_str}', version='{self.version}')"

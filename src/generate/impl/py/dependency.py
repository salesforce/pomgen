import generate
from functools import total_ordering


@total_ordering
class Dependency(generate.AbstractDependency):
    """
    Represents a Python package dependency.

    TODO - abstract common shape with maven dep into ABC.
    """

    def __init__(self, name, version, artifact_def=None, extras=None):
        self.name = name
        self.version = version
        self.artifact_def = artifact_def # TODO we don't want to store this
        self.extras = tuple(extras) if extras else ()

        self.child_dependencies = []

    # TODO impl in terms of label in crawler
    @property
    def references_artifact(self):
        if self.artifact_def is None:
            return True # 3rd party dep
        else:
            return self.artifact_def.generation_mode.produces_artifact

    def to_pyproject_format(self):
        """Convert the dependency to pyproject.toml format."""
        extras_str = ""
        if len(self.extras) > 0:
            extras_str = "[%s]" % ",".join(self.extras)
        return f"{self.name}{extras_str}>={self.version}"

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return False
        return (self.name == other.name and 
                self.version == other.version and
                self.extras == other.extras)

    def __lt__(self, other):
        return self.name < other.name

    def __hash__(self):
        return hash((self.name, self.version, self.extras))

    def __str__(self):
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{self.name}{extras_str}{self.version}"

    def __repr__(self):
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"Dependency(name='{self.name}{extras_str}', version='{self.version}')"

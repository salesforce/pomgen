import generate
from functools import total_ordering


@total_ordering
class PyDependency(generate.AbstractDependency):
    """
    Represents a Python package dependency.
    """

    def __init__(self, name, version, extras=None):
        assert name is not None
        assert version is not None
        assert extras is None or isinstance(extras, (list, tuple))
        self.name = name
        self.version = version
        self.extras = tuple(extras) if extras is not None else ()

    @property
    def native_repr(self):
        """Convert the dependency to pyproject.toml format."""
        extras_str = ""
        if len(self.extras) > 0:
            extras_str = "[%s]" % ",".join(self.extras)
        return f"{self.name}{extras_str}>={self.version}"

    def __eq__(self, other):
        if not isinstance(other, PyDependency):
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

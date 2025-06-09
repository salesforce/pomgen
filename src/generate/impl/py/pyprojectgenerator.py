TEMPLATE = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "$name$"
version = "$version$"
$dependencies$
requires-python = ">=3.11"
"""


class PyProjectGenerator:

    def __init__(self, artifact_def):
        self._artifact_def = artifact_def
        self._dependencies = set()
        self._dependencies_artifact_transitive_closure = set()
        self._dependencies_library_transitive_closure = set()

    # required currently, pomgen.py uses it, fix this
    @property
    def artifact_def(self):
        return self._artifact_def

    # required currently, pomgen.py uses it, fix this
    @property
    def bazel_package(self):
        return self._artifact_def.bazel_package

    def register_dependencies(self, dependencies):
        """
        Registers the dependencies the backing artifact references explicitly.

        """
        self._dependencies = dependencies

    def register_dependencies_transitive_closure__artifact(self, dependencies):
        """
        Registers the transitive closure of dependencies for the artifact
        (target) backing this pom generator.
        """
        self._dependencies_artifact_transitive_closure = dependencies

    def register_dependencies_transitive_closure__library(self, dependencies):
        """
        Registers the transitive closure of dependencies for the library
        that the artifact backing this pom generator belongs to.
        """
        self._dependencies_library_transitive_closure = dependencies

    def get_companion_generators(self):
        """
        Returns an iterable of companion generators. These manifests are not
        used as inputs to any generation algorithm; they are only part of the
        final outputs.

        Subclasses may implement.
        """
        return ()

    def gen(self, pomcontenttype):
        content = TEMPLATE.strip()
        content = content.replace("$name$", self._artifact_def.artifact_id)
        content = content.replace("$version$", self._artifact_def.version)
        if len(self._dependencies) == 0:
            content = content.replace("$dependencies$", "dependencies = []")
        else:
            content = content.replace(
                "$dependencies$",
                """dependencies = [
%s
]""" % "\n".join(['%s"%s",' % (" "*4, dep.to_pyproject_format()) for dep in self._dependencies]))
        return content

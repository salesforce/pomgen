import datetime


# TODO requires-python should not be hardcoded
_TEMPLATE = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "$name$"
version = "$version$"
requires-python = ">=3.9"
$dependencies$

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["*"]
"""


_VERSION_TS_TOKEN_START = "${timestamp:"
_VERSION_TS_TOKEN_END = "}"

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
        content = _TEMPLATE.strip()
        content = content.replace("$name$", self._artifact_def.artifact_id)
        content = content.replace("$version$", _get_version(self._artifact_def.version))
        if len(self._dependencies) == 0:
            content = content.replace("$dependencies$", "dependencies = []")
        else:
            deps = sorted(self._dependencies)
            content = content.replace(
                "$dependencies$",
                """dependencies = [
%s
]""" % "\n".join(['%s"%s",' % (" "*4, dep.to_pyproject_format()) for dep in deps]))
        return content



def _get_version(version):
    start_i = version.find(_VERSION_TS_TOKEN_START)
    if start_i != -1:
        end_i = version.index(_VERSION_TS_TOKEN_END, start_i)
        format_str = version[start_i + len(_VERSION_TS_TOKEN_START):end_i]
        timestamp = datetime.datetime.now().strftime(format_str)
        version = version[0:start_i] + timestamp + version[end_i+1:]
    return version

    

import datetime
import generate


_VERSION_TS_TOKEN_START = "${timestamp:"
_VERSION_TS_TOKEN_END = "}"


class PyProjectGenerator(generate.CommonManifestGenerator):

    def __init__(self, artifact_def, pyproject_template):
        super().__init__()
        self._artifact_def = artifact_def
        self._pyproject_template = pyproject_template.strip()
        assert len(self._pyproject_template) > 0, "pyproject template cannot be empty"

    def generate_release_manifest(self):
        """
        Generate release version of pyproject.toml.
        """
        content = self._pyproject_template.replace("$name$", self._artifact_def.artifact_id)
        content = content.replace("$version$", _get_version(self._artifact_def.version))
        if len(self.dependencies) == 0:
            content = content.replace("$dependencies$", "dependencies = []")
        else:
            deps = sorted(self.dependencies)
            content = content.replace(
                "$dependencies$",
                """dependencies = [
%s
]""" % "\n".join(['%s"%s",' % (" "*4, dep.native_repr) for dep in deps]))
        return content




def _get_version(version):
    start_i = version.find(_VERSION_TS_TOKEN_START)
    if start_i != -1:
        end_i = version.index(_VERSION_TS_TOKEN_END, start_i)
        format_str = version[start_i + len(_VERSION_TS_TOKEN_START):end_i]
        timestamp = datetime.datetime.now().strftime(format_str)
        version = version[0:start_i] + timestamp + version[end_i+1:]
    return version

    

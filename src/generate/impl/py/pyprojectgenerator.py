import generate


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
        content = content.replace("$version$", self.resolve_version(self._artifact_def.version))
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

    def read_metadata(self, manifest_path):
        raise NotImplementedError("read_metadata is not supported for pyproject.toml manifests")

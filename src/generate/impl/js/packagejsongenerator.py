import json
import generate
import os


class PackageJsonGenerator(generate.AbstractManifestGenerator):

    def __init__(self, repository_root, artifact_def, package_json_template):
        self._artifact_def = artifact_def
        self._package_json_template = package_json_template.strip()
        assert len(self._package_json_template) > 0, "package.json template cannot be empty"
        self._dev_package_json = PackageJsonGenerator._load_dev_package_json(repository_root, artifact_def)
        self._dependencies = set()
        self._dependencies_artifact_transitive_closure = set()
        self._dependencies_library_transitive_closure = set()

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
        return ()

    def generate_release_manifest(self):
        """
        Generate release version of package.json.
        """
        pack_json = self._package_json_template.replace("$dependencies$", '"dependencies": {}')
        pack_json = pack_json.replace("$name$", self._artifact_def.artifact_id)
        pack_json = pack_json.replace("$version$", self._artifact_def.version)
        main, types = self._get_main_and_types()
        pack_json = pack_json.replace("$main$", main)
        pack_json = pack_json.replace("$types$", types)
        package_dict = json.loads(pack_json)
        if len(self._dependencies) > 0:
            deps_dict = {}
            for dep in sorted(self._dependencies):
                deps_dict[dep.artifact_id] = f"^{dep.version}"
            package_dict["dependencies"] = deps_dict
        return json.dumps(package_dict, indent=4)

    def _get_main_and_types(self):
        main  = self._dev_package_json.get("main", "src/index.js")
        types = main[0:-2] + "d.ts"
        return main, types

    @classmethod
    def _load_dev_package_json(clazz, repository_root, artifact_def):
        assert repository_root is not None
        assert artifact_def.bazel_package is not None
        fname = os.path.join(repository_root, artifact_def.bazel_package, "package.json")
        if os.path.exists(fname):
            with open(fname, "r") as f:
                return json.load(f)
        return {}

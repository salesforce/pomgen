import json
import generate


class PackageJsonGenerator(generate.AbstractManifestGenerator):

    def __init__(self, artifact_def, package_json_template):
        self._artifact_def = artifact_def
        self._package_json_template = package_json_template.strip()
        assert len(self._package_json_template) > 0, "package.json template cannot be empty"
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
        # Parse template as JSON by temporarily replacing $dependencies$ with empty object
        template_for_parsing = self._package_json_template.replace("$dependencies$", '"dependencies": {}')
        template_for_parsing = template_for_parsing.replace("$name$", self._artifact_def.artifact_id)
        template_for_parsing = template_for_parsing.replace("$version$", self._artifact_def.version)
        package_dict = json.loads(template_for_parsing)

        # Build dependencies dict
        if len(self._dependencies) > 0:
            deps_dict = {}
            for dep in sorted(self._dependencies):
                deps_dict[dep.artifact_id] = f"^{dep.version}"
            package_dict["dependencies"] = deps_dict

        # Serialize to JSON with indentation
        return json.dumps(package_dict, indent=4)

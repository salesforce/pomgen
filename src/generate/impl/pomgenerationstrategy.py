import crawl.dependency as dependency
import generate


class PomGenerationStrategy(generate.AbstractGenerationStrategy):

    def __init__(self, workspace, pom_template):
        assert workspace is not None
        assert pom_template is not None
        self.workspace = workspace
        self.pom_template = pom_template

    def load_dependency(self, label, artifact_def):
        if label.is_source_ref:
            assert artifact_def is not None
            return dependency.new_dep_from_maven_artifact_def(artifact_def)
        else:
            if label.canonical_form not in self.workspace._label_to_ext_dep:
                print(self.workspace._label_to_ext_dep.values())
                raise Exception("Unknown external dependency - please make sure all maven install json files have been registered with pomgen (by setting maven_install_paths in the pomgen config file): [%s]" % label.canonical_form)
            return self.workspace._label_to_ext_dep[label.canonical_form]

    def load_dependency_by_native_repr(self, str_repr):
        if str_repr.count(":") == 1:
            str_repr += ":-1"
        return dependency.new_dep_from_maven_art_str(str_repr, None)

    def load_transitive_closure(self, dependency):
        depmd = self.workspace.dependency_metadata
        return depmd.get_transitive_closure(dependency)

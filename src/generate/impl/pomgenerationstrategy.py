import common.logger as logger
import crawl.dependency as dependency
import crawl.bazel as bazel
import crawl.pom as pom
import generate


class PomGenerationStrategy(generate.AbstractGenerationStrategy):

    def __init__(self,
                 repository_root,
                 config,
                 maven_install_info,
                 dependency_md,
                 pom_content_md,
                 label_to_overridden_fq_label,
                 verbose=False):
        assert repository_root is not None
        assert config is not None
        assert maven_install_info is not None
        assert dependency_md is not None
        assert pom_content_md is not None
        assert label_to_overridden_fq_label is not None
        self._repository_root = repository_root
        self._pom_template = config.pom_template
        self._maven_install_info = maven_install_info
        self._dependency_md = dependency_md
        self._pom_content_md = pom_content_md
        self._label_to_overridden_fq_label = label_to_overridden_fq_label
        self._verbose = verbose
        self._base_filename = config.pom_base_filename
        self._label_to_ext_dep = None

    def initialize(self):
        self._label_to_ext_dep = self._parse_maven_install()

    @property
    def metadata_path(self):
        return "MVN-INF/BUILD.pom"
    
    @property
    def released_manifest_path(self):
        # historically we have always used this filename
        return "MVN-INF/pom.xml.released"

    @property
    def base_manifest_filename(self):
        return self._base_filename

    @property
    def manifest_file_extension(self):
        return "xml"

    def load_dependency(self, label, artifact_def):
        if label.is_source_ref:
            assert artifact_def is not None
            return dependency.new_dep_from_maven_artifact_def(artifact_def)
        else:
            if label.canonical_form not in self._label_to_ext_dep:
                print(self._label_to_ext_dep.values())
                raise Exception("Unknown external dependency - please make sure all maven install json files have been registered with pomgen (by setting maven_install_paths in the pomgen config file): [%s]" % label.canonical_form)
            return self._label_to_ext_dep[label.canonical_form]

    def load_transitive_closure(self, dependency):
        return self._dependency_md.get_transitive_closure(dependency)

    def load_external_dependencies(self):
        assert self._label_to_ext_dep is not None
        return tuple(self._label_to_ext_dep.values())

    def _new_generator__hook(self, artifact_def):
        assert self._label_to_ext_dep is not None
        return pom.get_pom_generator(self._pom_template,
                                     artifact_def,
                                     tuple(self._label_to_ext_dep.values()),
                                     self._pom_content_md, self._dependency_md)

    def _parse_maven_install(self):
        """
        Parses all pinned json files for the specified maven_install rules.
        """
        names_and_paths = self._maven_install_info.\
            get_maven_install_names_and_paths(self._repository_root)

        dep_to_transitives = bazel.parse_maven_install(
            names_and_paths, self._label_to_overridden_fq_label, self._verbose)

        label_to_dep = {}
        for dep, transitives in dep_to_transitives:
            label = dep.bazel_label_name
            label_to_dep[label] = dep
            if self._verbose:
                logger.debug("Registered dep %s" % label)
            self._dependency_md.register_transitives(dep, transitives)
        return label_to_dep

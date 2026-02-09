import common.common as common
import common.logger as logger
import generate.impl.py.pydependency as pydependency
import generate.impl.py.pyprojectgenerator as pyprojectgenerator
import generate.impl.py.requirementsparser as requirementsparser
import generate
import os


class PyGenerationStrategy(generate.AbstractGenerationStrategy):

    def __init__(self, repository_root, config, verbose):
        assert repository_root is not None
        assert config is not None
        self._repository_root = repository_root
        self._locked_requirements_paths = config.locked_requirements_paths
        self._base_filename = config.pyproject_base_filename
        self._pyproject_template = config.pyproject_template
        self._verbose = verbose

    def initialize(self):
        self._label_to_ext_dep = self._parse_locked_requirements()

    @property
    def metadata_path(self):
        return "md/pyproject.in"

    @property
    def base_manifest_filename(self):
        return self._base_filename

    @property
    def manifest_file_extension(self):
        return "toml"

    def load_dependency(self, label, artifact_def):
        if label.is_source_ref:
            return pydependency.PyDependency.init_with_artifact_def(artifact_def)            
        else:
            assert label in self._label_to_ext_dep, "unknown third party dependency [%s]" % label
            return self._label_to_ext_dep[label]

    def load_dependency_by_native_repr(self, str_repr):
        return None

    def load_transitive_closure(self, dependency):
        return ()

    def _new_generator__hook(self, artifact_def):
        return pyprojectgenerator.PyProjectGenerator(artifact_def, self._pyproject_template)

    def _parse_locked_requirements(self):
        label_to_dep = {}
        for rel_path in self._locked_requirements_paths:
            # path/to/requirements_lock.txt@repository_name
            at_index = rel_path.find("@")
            assert at_index > 0, "Specify the path to the requirements.lock file, followed by \"@repository_name\", for example tools/pip/requirements_lock.txt@pip"
            repository_name = rel_path[at_index+1:]
            rel_path = rel_path[0:at_index]
            path = os.path.join(self._repository_root, rel_path)
            assert os.path.exists(path), "The requirements lock file path [%s] does not exist" % path
            content = common.read_file(path)
            parser = requirementsparser.RequirementsParser()
            if self._verbose:
                logger.info("Parsing locked file %s" % path)
            deps_pieces = parser.parse_requirements_lock_file(content)
            for name, version, extras in deps_pieces:
                dep = pydependency.PyDependency.init_with_name_and_version(name, version, extras, repository_name)
                label_to_dep[dep.label] = dep
                if self._verbose:
                    logger.info("  %s->%s" % (dep.label, dep))
        return label_to_dep

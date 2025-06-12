import common.common as common
import common.label as labelm
import common.logger as logger
import generate.impl.py.dependency as dependency
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
        """
        Load a dependency for a Python package.
        
        Args:
            label: The label for the dependency
            artifact_def: The artifact definition for source dependencies
            
        Returns:
            A dependency instance appropriate for Python packages
        """
        if label.is_source_ref:
            assert artifact_def is not None
            return dependency.Dependency(artifact_def.artifact_id, artifact_def.version, artifact_def)
        else:
            assert label in self._label_to_ext_dep, "unknown third party dependency [%s]" % label
            return self._label_to_ext_dep[label]

    def load_transitive_closure(self, dependency):
        return ()

    def _new_generator__hook(self, artifact_def):
        return pyprojectgenerator.PyProjectGenerator(artifact_def)

    def _parse_locked_requirements(self):
        label_to_dep = {}
        for rel_path in self._locked_requirements_paths:
            # path/to/requirements_lock.txt@repository_name
            at_index = rel_path.find("@")
            assert at_index > 0, "specify the path to the requirements.lock file, followed by \"@repository_name\", for example tools/pip/requirements_lock.txt@pip"
            repositoy_name = rel_path[at_index+1:]
            rel_path = rel_path[0:at_index]
            path = os.path.join(self._repository_root, rel_path)
            assert os.path.exists(path), "the requirements lock file path [%s] does not exist" % path
            content = common.read_file(path)
            parser = requirementsparser.RequirementsParser()
            deps = parser.parse_requirements_lock_file(content)
            if self._verbose and len(deps) > 0:
                logger.info("Parsing locked file %s" % path)
            for dep in deps:
                label_name = dep.name.replace("-", "_") # what else?
                lbl = labelm.Label("@%s//%s" % (repositoy_name, label_name)) 
                label_to_dep[lbl] = dep
                if self._verbose:
                    logger.info("  %s->%s" % (lbl, dep))
        return label_to_dep

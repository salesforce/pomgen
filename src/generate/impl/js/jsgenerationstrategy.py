import common.common as common
import common.label as label
import common.logger as logger
import generate.impl.js.jsdependency as jsdependency
import generate.impl.js.packagejsongenerator as packagejsongenerator
import generate.impl.js.pnpmlockparser as pnpmlockparser
import generate
import os


class JsGenerationStrategy(generate.AbstractGenerationStrategy):

    def __init__(self, repository_root, config, verbose):
        assert repository_root is not None
        assert config is not None
        self._repository_root = repository_root
        self._pnpm_lockfile_paths = config.pnpm_lockfile_paths
        self._base_filename = config.jspackage_base_filename
        self._jspackage_template = config.jspackage_template
        self._verbose = verbose
        self._label_to_ext_dep = {}
        self._dev_only_labels = []
        self._node_modules_label_prefixes = []

    def initialize(self):
        (self._label_to_ext_dep,
         self._dev_only_labels,
         self._node_modules_label_prefixes) =\
             JsGenerationStrategy._parse_pnpm_lockfiles(
                 self._repository_root,
                 self._pnpm_lockfile_paths,
                 self._verbose)

    @property
    def metadata_path(self):
        return "pack/package.in"

    @property
    def base_manifest_filename(self):
        return self._base_filename

    @property
    def manifest_file_extension(self):
        return "json"

    def _is_source_ref(self, lbl):
        return lbl.is_source_ref and not lbl.canonical_form.startswith("//examples/js:node_modules")

    def load_dependency(self, lbl, artifact_def):
        if self._is_source_ref(lbl):
            return jsdependency.JsDependency.init_with_artifact_def(artifact_def)
        else:
            if lbl in self._label_to_ext_dep:
                return self._label_to_ext_dep[lbl]
            elif lbl in self._dev_only_labels:
                # we do not include dev-only dependencies (@types typically)
                return None
            else:
                assert False, "Unknown label, this is a bug [%s]" % lbl

    def load_dependency_by_native_repr(self, str_repr):
        return None

    def load_transitive_closure(self, dependency):
        return ()

    def is_source_ref__hook(self, lbl):
        assert lbl.is_source_ref
        for prefix in self._node_modules_label_prefixes:
            if lbl.canonical_form.startswith(prefix):
                return False
        return True

    def _new_generator__hook(self, artifact_def):
        return packagejsongenerator.PackageJsonGenerator(artifact_def, self._jspackage_template)

    @classmethod
    def _parse_pnpm_lockfiles(clazz, repository_root, pnpm_lockfile_paths, verbose):
        label_to_dep = {}
        dev_dependency_labels = []
        label_prefixes = []
        repository_name = "npm"
        for rel_path in pnpm_lockfile_paths:
            path = os.path.join(repository_root, rel_path)
            assert os.path.exists(path), "The pnpm lock file path [%s] does not exist" % path
            content = common.read_file(path)
            parser = pnpmlockparser.PnpmLockParser()
            if verbose:
                logger.info("Parsing pnpm lock file %s" % path)
            runtime_deps_pieces, dev_only_deps_pieces = parser.parse_pnpm_lock_file(content)
            label_prefix = "//%s:node_modules" % os.path.dirname(rel_path)
            label_prefixes.append(label_prefix)
            for name, version in runtime_deps_pieces:
                dep = jsdependency.JsDependency.init_with_name_and_version(name, version, repository_name)
                lbl = label.Label("%s/%s" % (label_prefix, name))
                label_to_dep[lbl] = dep
                if verbose:
                    logger.info("  %s->%s" % (lbl, dep))
            for name, _ in dev_only_deps_pieces:
                lbl = label.Label("%s/%s" % (label_prefix, name))
                dev_dependency_labels.append(lbl)
        return label_to_dep, dev_dependency_labels, label_prefixes

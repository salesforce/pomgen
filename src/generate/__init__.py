from abc import ABC, abstractmethod
from functools import total_ordering
import common.label as labelm
import os


class AbstractManifestGenerator(ABC):
    """
    The manifest generator contract.
    """

    @abstractmethod
    def generate_release_manifest(self):
        """
        Returns the production manifest as a string.
        """
        pass

    def generate_goldfile_manifest(self):
        """
        Returns a version of the production manifest that is "stable", ie
        suitable for comparision against a previous version of the production
        manifest.
        """
        return self.generate_release_manifest()

    def format_for_comparison(self, manifest_content):
        """
        Formats the given golfile manifest for comparison.

        Hook to optionally modify manifest content before comaprison.

        TODO use explicit __hook naming?

        Args:
            manifest_content: The manifest content as a string

        Returns:
            The formatted manifest content as a string
        """
        return manifest_content


class AbstractGenerationStrategy(ABC):

    def initialize(self):
        """
        Called once before any other methods are called on this strategy
        instance.
        """
        pass

    @property
    @abstractmethod
    def metadata_path(self, path):
        pass

    @property
    @abstractmethod
    def base_manifest_filename(self):
        """
        The base filename of the generated manifest.
        """
        pass

    @property
    @abstractmethod
    def manifest_file_extension(self):
        """
        The filename extension of the generated manifest.
        """
        pass

    @property
    def released_metadata_path(self):
        return "%s.released" % self.metadata_path

    @property
    def released_manifest_path(self):
        md_dir_name = os.path.dirname(self.metadata_path)
        return os.path.join(md_dir_name, "%s.%s.released" % (self.base_manifest_filename, self.manifest_file_extension))

    @abstractmethod
    def load_dependency(self, label, artifact_def=None):
        """
        For the given label and artifact_def, returns a dependency instance.

        artifact_def is only provided if the label is a source ref, for example,
        if the label is //projects/libs/cool_lib1 then the artifact_def
        is the parsed artifact file for projects/libs/cool_lib1.

        Args:
            label common.label.Label, the label for which to return a
            dependency (AbstractDependency)
            artifact_def crawl.buildpom.MavenArfifactDef for source labels,
            the artifact the label points to
        Returns:
            AbstractDependency instance
        """
        pass

    @abstractmethod
    def load_dependency_by_native_repr(self, str_repr):
        pass

    @abstractmethod
    def load_transitive_closure(self, dependency):
        """
        Given a dependency instance, returns the transitive closure of
        all dependencies this given one references.

        This method is only called for 3rd party dependencies (for ex jar
        dependencies).

        We could use bazel query to get the same information, but it is
        faster to parse the "pinned dependency file" once.
        """
        pass

    def load_external_dependencies(self):
        """
        Returns an interable of external dependencies, so all dependencies
        that are never build in the source code repository.
        """
        return ()

    def new_generator(self, ctx):
        """
        Configures and returns a new manifest generator.
        """
        gen = self._new_generator__hook(ctx.artifact_def)
        gen.register_dependencies(ctx.direct_dependencies)
        gen.register_dependencies_transitive_closure__artifact(ctx.artifact_transitive_closure)
        gen.register_dependencies_transitive_closure__library(ctx.library_transitive_closure)
        return gen
        
    @abstractmethod
    def _new_generator__hook(self, artifact_def):
        """
        Returns a new AbstractManifestGenerator instance.

        Hook method, only meant to be called from this class
        and optionally implementeded in subclasses.
        """
        pass


@total_ordering
class AbstractDependency(ABC):

    def __init__(self, label, artifact_def, artifact_id=None, version=None):
        if artifact_def is None:
            assert isinstance(label, labelm.Label)
            self._label = label
            self._artifact_def = None
            assert artifact_id is not None
            self._artifact_id = artifact_id
            self._version = version
        else:
            assert label is None, "pass in label as None, it will be built here"
            self._label = labelm.Label(artifact_def.bazel_package)
            if artifact_def.bazel_target is not None:
                self._label = self._label.with_target(artifact_def.bazel_target)
            self._artifact_def = artifact_def
            assert artifact_id is None
            self._artifact_id = artifact_def.artifact_id
            assert version is None

    @property
    @abstractmethod
    def native_repr(self):
        raise Exception("Must be implemented in subclasses")
    
    @property
    def label(self):
        return self._label

    @property
    def artifact_id(self):
        return self._artifact_id

    @property
    def version(self):
        if self._artifact_def is None:
            return self._version
        else:
            use_released = self._use_previously_released_artifact()
            return self._artifact_def.released_version if use_released else self._artifact_def.version

    def _use_previously_released_artifact(self):
        if self._artifact_def.requires_release is not None:
            # better to be explicit here: requires_release has been set
            if self._artifact_def.requires_release == False: # noqa: E712
                return True
        return False

    # note that hash/eq/lt etc don't use the version because
    # the version can change based on the value of requires_release
    # we need to check whether we can create dependency instances after
    # the value of requires release is known so we can make this more consistent
    def __hash__(self):
        return hash((self._artifact_id))

    def __eq__(self, other):
        if self is other:
            return True
        return self._artifact_id == other._artifact_id

    def __lt__(self, other):
        return self._artifact_id < other._artifact_id

    def __str__(self):
        s = "%s %s" % (self.native_repr, "(local)" if self.label.is_source_ref else "")
        return s.strip()

    def __repr__(self):
        return self.__str__()

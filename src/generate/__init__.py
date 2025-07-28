from abc import ABC, abstractmethod
import os


class AbstractDependency(ABC):
    """
    TODO for source dependencies, abstract here how we decide whether a 
    previously released version should be used or not
    """
    pass


class AbstractManifestGenerator(ABC):
    """
    TODO add dependencies related methods
    """

    @abstractmethod
    def gen():
        pass


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
    def load_dependency(self, label, artifact_def):
        """
        For the given label and artifact_def, returns a dependency instance.

        artifact_def is provided if the label is a source ref, for example,
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

        Hook method, only meant to be implementation in subclasses.
        """
        pass

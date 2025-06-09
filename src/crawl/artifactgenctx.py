class ArtifactGenerationContext:
    """
    Information about a single artifact that was crawled.
    """

    def __init__(self, workspace, artifact_def, label):
        self._artifact_def = artifact_def
        self._label = label
        self._direct_dependencies = None
        self._artifact_transitive_closure = None
        self._library_transitive_closure = None

    @property
    def artifact_def(self):
        """
        The artifact that this context is for.
        """
        return self._artifact_def

    @property
    def label(self):
        """
        The label that points at this artifact.
        """
        return self._label

    @property
    def direct_dependencies(self):
        assert self._direct_dependencies is not None
        return self._direct_dependencies

    @property
    def artifact_transitive_closure(self):
        assert self._artifact_transitive_closure is not None
        return self._artifact_transitive_closure

    @property
    def library_transitive_closure(self):
        assert self._library_transitive_closure is not None
        return self._library_transitive_closure

    def register_artifact_directs(self, dependencies):
        """
        Registers the dependencies this artifact references explicitly.
        """
        self._direct_dependencies = dependencies

    def register_artifact_transitive_closure(self, dependencies):
        """
        Registers the transitive closure of dependencies of this artifact.
        """
        self._artifact_transitive_closure = dependencies

    def register_library_transitive_closure(self, dependencies):
        """
        Registers the transitive closure of dependencies of the library
        that this artifact belongs to.
        """
        self._library_transitive_closure = dependencies

import crawl.pom


class ArtifactGenerationContext:
    """
    Information about a single artifact that was crawled.
    """

    def __init__(self, workspace, pom_template, artifact_def, label, excluded_deps):
        self._artifact_def = artifact_def
        self._label = label

        self._direct_dependencies = []
        self._artifact_transitive_closure = []
        self._library_transitive_closure = []

        self._generator = crawl.pom.get_pom_generator(
            workspace, pom_template, artifact_def, excluded_deps)

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
        return self._direct_dependencies

    @property
    def artifact_transitive_closure(self):
        return self._artifact_transitive_closure

    @property
    def library_transitive_closure(self):
        return self._library_transitive_closure

    @property
    def generator(self):
        return self._generator

    def register_artifact_directs(self, dependencies):
        """
        Registers the dependencies this artifact references explicitly.
        """
        self._direct_dependencies = dependencies
        self._generator.register_dependencies(dependencies)

    def register_artifact_transitive_closure(self, dependencies):
        """
        Registers the transitive closure of dependencies of this artifact.
        """
        self._artifact_transitive_closure = dependencies
        self._generator.register_dependencies_transitive_closure__artifact(dependencies)

    def register_library_transitive_closure(self, dependencies):
        """
        Registers the transitive closure of dependencies of the library
        that this artifact belongs to.
        """
        self._library_transitive_closure = dependencies
        self._generator.register_dependencies_transitive_closure__library(dependencies)

    def gen_goldfile_manifest(self):
        """
        TODO - fix abstraction - move to after crawling?
        """
        import crawl.pom
        return self._generator.gen(crawl.pom.PomContentType.GOLDFILE)

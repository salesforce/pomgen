import generator


class PomGenerationStrategy(generator.AbstractGenerationStrategy):

    def __init__(self, workspace):
        self.workspace = workspace

    def load_dependencies(self, labels):
        """
        For the given label instances, returns a list of dependencies.
        """
        pass


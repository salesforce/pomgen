from abc import ABC, abstractmethod


class AbstractDependency(ABC):
    pass


class AbstractGenerationStrategy(ABC):

    @abstractmethod
    def load_dependencies(self, labels):
        """
        For the given label instances, returns a list of dependencies.
        """
        pass

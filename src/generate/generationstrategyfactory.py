from common import mdfiles
import generate.impl.pom.pomgenerationstrategy as pomgenerationstrategy
import generate.impl.py.pygenerationstrategy as pygenerationstrategy
import os


class GenerationStrategyFactory:
    
    def __init__(self, repository_root, config, manifest_content, verbose):
        assert repository_root is not None
        assert config is not None
        assert manifest_content is not None
        self._repository_root = repository_root
        self._verbose = verbose
        self._strategies = []
        self._pomstrategy = pomgenerationstrategy.PomGenerationStrategy.new(
            repository_root, config, manifest_content, verbose)
        self._strategies = (
            self._pomstrategy,
            pygenerationstrategy.PyGenerationStrategy(
                self._repository_root, config, self._verbose))
        self._initialize_strategies()

    def get_strategy_for_package(self, package):
        for strategy in self._strategies:
            if os.path.exists(os.path.join(self._repository_root, package,
                                           strategy.metadata_path)):
                return strategy
        return None

    def get_strategy_for_library_package(self, package):
        for strategy in self._strategies:
            md_dir_name = os.path.dirname(strategy.metadata_path)
            path = os.path.join(self._repository_root, package, md_dir_name,
                                mdfiles.LIB_ROOT_FILE_NAME)
            if os.path.exists(path):
                return strategy
        return None

    def load_all_external_dependencies(self):
        # leaky - only for poms at this point, review usages
        return self._pomstrategy.load_external_dependencies()

    def _initialize_strategies(self):
        for strategy in self._strategies:
            strategy.initialize()

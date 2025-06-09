from common import maveninstallinfo
from common import overridefileinfo
from crawl import dependencymd as dependencym
from common import mdfiles
from generate.impl import pomgenerationstrategy
from generate.impl import pygenerationstrategy
import os


class GenerationStrategyFactory:
    
    def __init__(self, repository_root, config, pom_content, verbose):
        assert repository_root is not None
        assert config is not None
        assert pom_content is not None
        self._repository_root = repository_root
        self._verbose = verbose
        self._strategies = []
        self._pomstrategy = self._build_pomgen_strategy(config, pom_content)
        self._strategies = (self._pomstrategy, self._build_pygen_strategy(config))
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

    def _build_pomgen_strategy(self, config, pom_content):
        dependencymd = dependencym.DependencyMetadata(
            config.jar_artifact_classifier)
        override_file_info = overridefileinfo.OverrideFileInfo(
            config.override_file_paths, self._repository_root)
        mvn_install_info = maveninstallinfo.MavenInstallInfo(
            config.maven_install_paths)
        return pomgenerationstrategy.PomGenerationStrategy(
            self._repository_root, config, mvn_install_info, dependencymd,
            pom_content, override_file_info.label_to_overridden_fq_label,
            self._verbose)

    def _build_pygen_strategy(self, config):
        return pygenerationstrategy.PyGenerationStrategy(
            self._repository_root, config, self._verbose)

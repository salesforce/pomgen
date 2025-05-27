import generate


class PyGenerationStrategy(generate.AbstractGenerationStrategy):
    """
    Strategy for generating Python package metadat as pyproject.toml.

    [build-system]
    requires = ["setuptools>=42", "wheel"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "hello-world"
    version = "0.1.0"
    description = "A sample Python project"
    readme = "README.md"
    requires-python = ">=3.8"
    license = {text = "Apache-2.0"}
    authors = [
        {name = "Your Name", email = "your.email@example.com"}
    ]
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]

    dependencies = [
        "requests>=2.28.0",
        "pytest>=7.0.0",
        "black>=22.0.0",
    ]
    """

    def __init__(self, workspace, template):
        assert workspace is not None
        assert template is not None
        self.workspace = workspace
        self.template = template

    def load_dependency(self, label, artifact_def):
        """
        Load a dependency for a Python package.
        
        Args:
            label: The label for the dependency
            artifact_def: The artifact definition for source dependencies
            
        Returns:
            A dependency instance appropriate for Python packages
        """
        pass

    def load_transitive_closure(self, dependency):
        pass

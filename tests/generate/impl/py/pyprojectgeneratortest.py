import unittest

import crawl.buildpom as buildpom
import generate.impl.py.pydependency as pydependency
import generate.impl.py.pyprojectgenerator as pyprojectgenerator


_TEMPLATE = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "$name$"
version = "$version$"
requires-python = ">=3.12"
$dependencies$

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["*"]
"""


class PyProjectGeneratorTest(unittest.TestCase):

    def test_generate(self):
        art_def = buildpom.MavenArtifactDef(artifact_id="a2", version="1.2.3")
        dep = pydependency.PyDependency.init_with_name_and_version("foodep", "1.2.3", (), "foo")
        gen = pyprojectgenerator.PyProjectGenerator(art_def, _TEMPLATE)
        gen.register_dependencies((dep,))

        pyproject = gen.generate_release_manifest()

        self.assertIn('name = "a2"', pyproject)
        self.assertIn('version = "1.2.3"', pyproject)
        self.assertIn("foodep>=1.2.3", pyproject)


if __name__ == '__main__':
    unittest.main()

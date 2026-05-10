import unittest

import crawl.buildpom as buildpom
import generate.impl.js.jsdependency as jsdependency
import generate.impl.js.packagejsongenerator as packagejsongenerator


_TEMPLATE = """{
    "name": "$name$",
    "version": "$version$",
    "main": "src/index.js",
    "types": "src/index.d.ts",
    $dependencies$
}"""


class PackageJsonGeneratorTest(unittest.TestCase):

    def test_generate(self):
        repository_root = ""
        art_def = buildpom.MavenArtifactDef(artifact_id="my-package", version="1.2.3", bazel_package="p1")
        dep = jsdependency.JsDependency.init_with_name_and_version("foo-dep", "4.5.6", "npm")
        gen = packagejsongenerator.PackageJsonGenerator(repository_root, art_def, _TEMPLATE)
        gen.register_dependencies((dep,))

        package_json = gen.generate_release_manifest()

        self.assertIn('"name": "my-package"', package_json)
        self.assertIn('"version": "1.2.3"', package_json)
        self.assertIn('"foo-dep": "^4.5.6"', package_json)

    def test_generate_no_dependencies(self):
        repository_root = ""
        art_def = buildpom.MavenArtifactDef(artifact_id="my-package", version="1.0.0", bazel_package="p1")
        gen = packagejsongenerator.PackageJsonGenerator(repository_root, art_def, _TEMPLATE)
        gen.register_dependencies(())

        package_json = gen.generate_release_manifest()

        self.assertIn('"name": "my-package"', package_json)
        self.assertIn('"version": "1.0.0"', package_json)
        self.assertIn('"dependencies": {}', package_json)

    def test_generate_multiple_dependencies(self):
        repository_root = ""
        art_def = buildpom.MavenArtifactDef(artifact_id="my-package", version="2.0.0", bazel_package="p1")
        dep1 = jsdependency.JsDependency.init_with_name_and_version("dep-a", "1.0.0", "npm")
        dep2 = jsdependency.JsDependency.init_with_name_and_version("dep-b", "2.0.0", "npm")
        gen = packagejsongenerator.PackageJsonGenerator(repository_root, art_def, _TEMPLATE)
        gen.register_dependencies((dep1, dep2))

        package_json = gen.generate_release_manifest()

        self.assertIn('"dep-a": "^1.0.0"', package_json)
        self.assertIn('"dep-b": "^2.0.0"', package_json)
        self.assertIn('"dependencies": {', package_json)


if __name__ == '__main__':
    unittest.main()

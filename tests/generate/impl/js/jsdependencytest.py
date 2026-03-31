import crawl.buildpom as buildpom
import generate.impl.js.jsdependency as jsdependency
import unittest


class JsDependencyTest(unittest.TestCase):

    def test_from_artifact_def(self):
        pack = "a/b/c"
        art_def = buildpom.MavenArtifactDef("", "name22", "100", bazel_package=pack, bazel_target="t1")

        dep = jsdependency.JsDependency.init_with_artifact_def(art_def)

        self.assertEqual(dep.artifact_id, "name22")
        self.assertEqual(dep.version, "100")
        self.assertEqual(dep.native_repr, '"name22": "^100"')
        self.assertEqual(dep.label.canonical_form, "//a/b/c:t1")

    def test_from_components(self):
        dep = jsdependency.JsDependency.init_with_name_and_version("myname", "1.2.3", "repo")

        self.assertEqual(dep.artifact_id, "myname")
        self.assertEqual(dep.version, "1.2.3")
        self.assertEqual(dep.native_repr, '"myname": "^1.2.3"')
        self.assertEqual(dep.label.canonical_form, "@repo//myname")


if __name__ == '__main__':
    unittest.main()

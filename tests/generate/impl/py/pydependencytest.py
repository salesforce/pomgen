import common.genmode as genmode
import crawl.buildpom as buildpom
import generate.impl.py.pydependency as pydependency
import unittest


class PyDependencyTest(unittest.TestCase):

    def test_from_artifact_def(self):
        pack = "a/b/c"
        art_def = buildpom.MavenArtifactDef("", "name22", "100", bazel_package=pack, bazel_target="t1")
        art_def = buildpom._augment_art_def_values(art_def, None, pack, "INF", None, None, genmode.DYNAMIC)

        dep = pydependency.PyDependency.init_with_artifact_def(art_def)

        self.assertEqual(dep.artifact_id, "name22")
        self.assertEqual(dep.version, "100")
        self.assertEqual(len(dep.extras), 0)
        self.assertEqual(dep.native_repr, "name22>=100")
        self.assertEqual(dep.label.canonical_form, "//a/b/c:t1")

    def test_from_components(self):
        dep = pydependency.PyDependency.init_with_name_and_version("myname", "1.2.3", ["a", "b", "c"], "repo")

        self.assertEqual(dep.artifact_id, "myname")
        self.assertEqual(dep.version, "1.2.3")
        self.assertEqual(dep.extras, ("a", "b", "c"))
        self.assertEqual(dep.native_repr, "myname[a,b,c]>=1.2.3")
        self.assertEqual(dep.label.canonical_form, "@repo//myname")


if __name__ == '__main__':
    unittest.main()

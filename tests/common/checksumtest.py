import common.checksum as checksum
import crawl.buildpom as buildpom
import generate.impl.pom.dependency as dependency
import unittest


class ChecksumTest(unittest.TestCase):

    def setUp(self):
        self.ext_dep_a = dependency.new_dep_from_maven_art_str("a:a:1.0.0", "m")
        self.ext_dep_z = dependency.new_dep_from_maven_art_str("z:z:1.0.0", "m")
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0.0", bazel_package="pack1")
        self.int_dep = dependency.new_dep_from_maven_artifact_def(art_def)

    def test_nonzero_checksum(self):
        self.assertNotEqual(0, checksum.compute_for_external_dependencies([self.ext_dep_a]))

    def test_same_instance(self):
        self.assertEqual(
            checksum.compute_for_external_dependencies([self.ext_dep_a]),
            checksum.compute_for_external_dependencies([self.ext_dep_a]))

    def test_diff_instance(self):
        self.assertEqual(
            checksum.compute_for_external_dependencies([self.ext_dep_a]),
            checksum.compute_for_external_dependencies([dependency.new_dep_from_maven_art_str("a:a:1.0.0", "different")]))

    def test_version_matters(self):
        self.assertNotEqual(
            checksum.compute_for_external_dependencies([self.ext_dep_a]),
            checksum.compute_for_external_dependencies([dependency.new_dep_from_maven_art_str("a:a:2.0.0", "m")]))

    def test_ext_deps_only(self):
        cs = checksum.compute_for_external_dependencies([self.ext_dep_a])

        self.assertEqual(cs, checksum.compute_for_external_dependencies([self.int_dep, self.ext_dep_a]))

    def test_order_does_not_matter(self):
        self.assertEqual(
            checksum.compute_for_external_dependencies([self.ext_dep_z, self.ext_dep_a, self.int_dep]),
            checksum.compute_for_external_dependencies([self.ext_dep_a, self.int_dep, self.ext_dep_z]))

    def test_container_does_not_matter(self):
        cs = checksum.compute_for_external_dependencies([self.ext_dep_a, self.ext_dep_z])

        self.assertEqual(cs, checksum.compute_for_external_dependencies(set([self.ext_dep_a, self.ext_dep_z])))
        self.assertEqual(cs, checksum.compute_for_external_dependencies((self.ext_dep_a, self.ext_dep_z)))


if __name__ == '__main__':
    unittest.main()

import common.checksum as checksum
import crawl.buildpom as buildpom
import generate.impl.pom.dependency as dependency
import unittest


class ChecksumTest(unittest.TestCase):

    def setUp(self):
        self.ext_dep_a_v1 = dependency.new_dep_from_maven_art_str("a:a:1.0.0", "m")
        self.ext_dep_a_v2 = dependency.new_dep_from_maven_art_str("a:a:2.0.0", "m")
        self.ext_dep_z = dependency.new_dep_from_maven_art_str("z:z:1.0.0", "m")
        self.int_dep_a_v1 = dependency.new_dep_from_maven_artifact_def(
            buildpom.MavenArtifactDef("g", "a", "1.0.0", bazel_package="p1"))
        self.int_dep_a_v2 = dependency.new_dep_from_maven_artifact_def(
            buildpom.MavenArtifactDef("g", "a", "2.0.0", bazel_package="p1"))
        self.int_dep_z = dependency.new_dep_from_maven_artifact_def(
            buildpom.MavenArtifactDef("g", "zzz", "1.2.3", bazel_package="p1"))

    def test_nonzero_checksum(self):
        self.assertNotEqual(0, checksum.for_dependencies([self.ext_dep_a_v1]))

    def test_same_instance(self):
        self.assertEqual(
            checksum.for_dependencies([self.ext_dep_a_v1]),
            checksum.for_dependencies([self.ext_dep_a_v1]))

    def test_diff_instance(self):
        self.assertEqual(
            checksum.for_dependencies([self.ext_dep_a_v1]),
            checksum.for_dependencies([dependency.new_dep_from_maven_art_str("a:a:1.0.0", "different")]))

    def test_int_and_ext_dep(self):
        self.assertNotEqual(
            checksum.for_dependencies([self.ext_dep_a_v1]),
            checksum.for_dependencies([self.ext_dep_a_v1, self.int_dep_a_v1]))

    def test_int_dep_version_does_not_matter(self):
        self.assertEqual(
            checksum.for_dependencies([self.int_dep_a_v1]),
            checksum.for_dependencies([self.int_dep_a_v2]))

        self.assertNotEqual(
            checksum.for_dependencies([self.int_dep_a_v1]),
            checksum.for_dependencies([self.int_dep_z]))

    def test_version_matters_for_ext_dep(self):
        self.assertNotEqual(
            checksum.for_dependencies([self.ext_dep_a_v1]),
            checksum.for_dependencies([self.ext_dep_a_v2]))

    def test_order_does_not_matter(self):
        self.assertEqual(
            checksum.for_dependencies([self.ext_dep_z, self.ext_dep_a_v1, self.int_dep_a_v1]),
            checksum.for_dependencies([self.ext_dep_a_v1, self.int_dep_a_v1, self.ext_dep_z]))

    def test_container_does_not_matter(self):
        cs = checksum.for_dependencies([self.ext_dep_a_v1, self.ext_dep_z])

        self.assertEqual(cs, checksum.for_dependencies(set([self.ext_dep_a_v1, self.ext_dep_z])))
        self.assertEqual(cs, checksum.for_dependencies((self.ext_dep_a_v1, self.ext_dep_z)))

    def test_rm_version(self):
        self.assertEqual("a:a:", checksum._rm_version(self.ext_dep_a_v1.native_repr, self.ext_dep_a_v1.version))
        self.assertEqual("a:a:", checksum._rm_version(self.ext_dep_a_v2.native_repr, self.ext_dep_a_v2.version))
        self.assertEqual("g:a:", checksum._rm_version(self.int_dep_a_v2.native_repr, self.int_dep_a_v2.version))
        self.assertEqual("g:zzz:", checksum._rm_version(self.int_dep_z.native_repr, self.int_dep_z.version))


if __name__ == '__main__':
    unittest.main()

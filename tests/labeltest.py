from common import label
import unittest


class LabelTest(unittest.TestCase):

    def test_wildcard(self):
        n1 = label.Label("//foo/blah:foo")

        self.assertEqual(label.Label("//foo/blah/..."),
                         n1.as_wildcard_label("..."))
        self.assertEqual(label.Label("//foo/blah:*"),
                         n1.as_wildcard_label("*"))

    def test_with_target(self):
        n1 = label.Label("//foo/blah:foo")
        self.assertEqual(label.Label("//foo/blah:blah"),
                         n1.with_target("blah"))

    def test_invalid(self):
        n1 = label.Label("//foo/blah/")
        self.assertEqual("//foo/blah", n1.name)

    def test_name(self):
        n = label.Label("name")
        self.assertEqual("name", n.name)

    def test_package(self):
        n = label.Label("name")
        self.assertEqual("name", n.package)

        n = label.Label("name:foo/blah")
        self.assertEqual("name", n.package)

        n = label.Label("name:foo/blah:goo")
        self.assertEqual("name", n.package)

        n = label.Label("name/foo/...")
        self.assertEqual("name/foo/", n.package)

        n = label.Label("...")
        self.assertEqual("", n.package)

        n = label.Label("//...")
        self.assertEqual("//", n.package)

    def test_package_path(self):
        n = label.Label("name")
        self.assertEqual("name", n.package_path)

        n = label.Label("//dir1/dir2:foo/blah")
        self.assertEqual("dir1/dir2", n.package_path)

        n = label.Label("//name/name2")
        self.assertEqual("name/name2", n.package_path)

        n = label.Label("//name/name2/...")
        self.assertEqual("name/name2", n.package_path)

        n = label.Label("name/foo/...")
        self.assertEqual("name/foo", n.package_path)

        n = label.Label("...")
        self.assertEqual("", n.package_path)

        n = label.Label("//...")
        self.assertEqual("", n.package_path)

    def test_target(self):
        n = label.Label("//:name")
        self.assertEqual("name", n.target)
        self.assertEqual("name", n.target_name)

        n = label.Label("name:foo/blah")
        self.assertEqual("foo/blah", n.target)
        self.assertEqual("foo/blah", n.target_name)

        n = label.Label("name:foo/blah:goo")
        self.assertEqual("foo/blah:goo", n.target)
        self.assertEqual("foo/blah:goo", n.target_name)

        n = label.Label("a/b/c")
        self.assertEqual("c", n.target)
        self.assertEqual("c", n.target_name)

        n = label.Label("//foo")
        self.assertEqual("foo", n.target)
        self.assertEqual("foo", n.target_name)

        n = label.Label("foo")
        self.assertEqual("foo", n.target)
        self.assertEqual("foo", n.target_name)

        n = label.Label(":foo")
        self.assertEqual("foo", n.target)
        self.assertEqual("foo", n.target_name)

    def test_is_default_target(self):
        n = label.Label("//name")
        self.assertTrue(n.is_default_target)

        n = label.Label("name:name")
        self.assertTrue(n.is_default_target)

        n = label.Label("//name:foo")
        self.assertFalse(n.is_default_target)

    def test_alternate_default_target_syntax(self):
        n1 = label.Label("//a/b/c")
        alt = n1.as_alternate_default_target_syntax()
        self.assertTrue(isinstance(alt, label.Label))
        self.assertEqual("//a/b/c:c", str(alt.name))

        n1 = label.Label("//a/b/c:c")
        alt = n1.as_alternate_default_target_syntax()
        
        self.assertTrue(isinstance(alt, label.Label))
        self.assertEqual("//a/b/c", str(alt.name))


    def test_alternate_default_target_syntax__error_on_non_default(self):
        n1 = label.Label("//a/b/c:foo")

        with self.assertRaises(Exception):
            n1.as_alternate_default_target_syntax()

    def test_is_root_target(self):
        n = label.Label("//name")
        self.assertFalse(n.is_root_target)

        n = label.Label("@pomgen//:query")
        self.assertTrue(n.is_root_target)

        n = label.Label("//:query")
        self.assertTrue(n.is_root_target)

    def test_is_private(self):
        n = label.Label("name")
        self.assertFalse(n.is_private)

        n = label.Label(":name")
        self.assertTrue(n.is_private)

    def test_fqname(self):
        n = label.Label("name")
        self.assertEqual("@maven//:name", n.fqname)

        n = label.Label("@bazel//:name")
        self.assertEqual("@bazel//:name", n.fqname)

        n = label.Label("//foo/blah")
        self.assertEqual("//foo/blah", n.fqname)

    def test_simple_name(self):
        n = label.Label("name")
        self.assertEqual("name", n.simple_name)

        n = label.Label("@bazel//:name")
        self.assertEqual("name", n.simple_name)

        n = label.Label("//foo/blah")
        self.assertEqual("//foo/blah", n.simple_name)

    def test_has_repo_prefix(self):
        n = label.Label("name")
        self.assertFalse(n.has_repo_prefix)

        n = label.Label("@foo//:name")
        self.assertTrue(n.has_repo_prefix)

        n = label.Label("@pomgen//maven")
        self.assertTrue(n.has_repo_prefix)

    def test_repo_prefix(self):
        n = label.Label("name")
        self.assertIsNone(n.repo_prefix)

        n = label.Label("@foo//:name")
        self.assertEqual("foo", n.repo_prefix)

        n = label.Label("@pomgen//maven")
        self.assertEqual("pomgen", n.repo_prefix)

    def test_has_extension_suffix(self):
        n = label.Label("name-extension")
        self.assertFalse(n.has_extension_suffix)

        n = label.Label("name_extension")
        self.assertTrue(n.has_extension_suffix)

    def test_is_source_ref(self):
        n = label.Label("name-extension")
        self.assertFalse(n.is_source_ref)

        n = label.Label("//name_extension")
        self.assertTrue(n.is_source_ref)

    def test_has_file_extension(self):
        n = label.Label("name")
        self.assertFalse(n.has_file_extension)

        n = label.Label("name.jar")
        self.assertTrue(n.has_file_extension)

    def test_is_source_artifact(self):
        n = label.Label("name")
        self.assertFalse(n.is_sources_artifact)

        n = label.Label("name_jar_sources.jar")
        self.assertTrue(n.is_sources_artifact)

    def test_len(self):
        self.assertEqual(4, len(label.Label("1234")))

    def test_hash(self):
        n1 = label.Label("1234")
        n2 = label.Label("1234")
        self.assertEqual(hash(n1), hash(n2))

        n1 = label.Label("a/b/c")
        n2 = label.Label("a/b/c:c")
        self.assertEqual(hash(n1), hash(n2))

    def test_eq(self):
        n1 = label.Label("1234")
        n2 = label.Label("1234")
        self.assertEqual(n1, n2)
        self.assertFalse(n1 != n2)

        # n1 specifies the default target, n2 does not, the labels
        # are equal
        n1 = label.Label("//a/b/c:c")
        n2 = label.Label("//a/b/c")
        self.assertEqual(n1, n2)
        self.assertFalse(n1 != n2)

        n1 = label.Label("1234")
        n2 = label.Label("4567")
        self.assertNotEqual(n1, n2)
        self.assertFalse(n1 == n2)

        n1 = label.Label("a/b/c")
        n2 = label.Label("//a/b/c")
        self.assertEqual(n1, n2)
        self.assertFalse(n1 != n2)

    def test_build_file(self):
        n1 = label.Label("a/b/c/BUILD")
        self.assertEqual("a/b/c", n1.package)
        self.assertEqual("a/b/c/BUILD", n1.build_file_path)

        n1 = label.Label("a/b/c/BUILD.bazel")
        self.assertEqual("a/b/c", n1.package)
        self.assertEqual("a/b/c/BUILD.bazel", n1.build_file_path)

        n1 = label.Label("a/b/c/BUILDER")
        self.assertEqual("a/b/c/BUILDER", n1.package)
        self.assertIsNone(n1.build_file_path)


if __name__ == '__main__':
    unittest.main()

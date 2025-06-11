from common import label
import unittest


class LabelTest(unittest.TestCase):

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

        n = label.Label("@foo//a/b/c")
        self.assertEqual("a/b/c", n.package_path)

    def test_target(self):
        n = label.Label("//:name")
        self.assertEqual("name", n.target)

        n = label.Label("name:foo/blah")
        self.assertEqual("foo/blah", n.target)

        n = label.Label("name:foo/blah:goo")
        self.assertEqual("goo", n.target)

        n = label.Label("a/b/c")
        self.assertEqual("c", n.target)

        n = label.Label("//foo")
        self.assertEqual("foo", n.target)

        n = label.Label("foo")
        self.assertEqual("foo", n.target)

        n = label.Label(":foo")
        self.assertEqual("foo", n.target)

    def test_is_root_target(self):
        n = label.Label("//name")
        self.assertFalse(n.is_root_target)

        n = label.Label("@poppy//:query")
        self.assertTrue(n.is_root_target)

        n = label.Label("//:query")
        self.assertTrue(n.is_root_target)

    def test_has_repository_prefix(self):
        n = label.Label("name")
        self.assertFalse(n.has_repository_prefix)

        n = label.Label("@foo//:name")
        self.assertTrue(n.has_repository_prefix)

        n = label.Label("@poppy//maven")
        self.assertTrue(n.has_repository_prefix)

    def test_repository_prefix(self):
        n = label.Label("name")
        self.assertEqual("", n.repository_prefix)

        n = label.Label("@foo//:name")
        self.assertEqual("@foo", n.repository_prefix)

        n = label.Label("@poppy//maven")
        self.assertEqual("@poppy", n.repository_prefix)

    def test_hash(self):
        n1 = label.Label("@foo//blah:1234")
        n2 = label.Label("@foo//blah:1234")
        self.assertEqual(hash(n1), hash(n2))

        n1 = label.Label("a/b/c")
        n2 = label.Label("a/b/c:c")
        self.assertEqual(hash(n1), hash(n2))

        n1 = label.Label("a/b/c")
        n2 = label.Label("@foo//a/b/c:c")
        self.assertNotEqual(hash(n1), hash(n2))

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

    def test_trailing_slash(self):
        n1 = label.Label("//foo/blah/")
        self.assertEqual("blah", n1.target)

    def test_canonical_form(self):
        n1 = label.Label("foo")
        self.assertEqual("//foo", n1.canonical_form)

        n1 = label.Label("//:foo")
        self.assertEqual("//:foo", n1.canonical_form)

        n1 = label.Label("//path/blah:foo")
        self.assertEqual("//path/blah:foo", n1.canonical_form)

        n1 = label.Label("//path/blah:blah")
        self.assertEqual("//path/blah", n1.canonical_form)

        n1 = label.Label("@poppy//blah:foo")
        self.assertEqual("@poppy//blah:foo", n1.canonical_form)

        n1 = label.Label("@poppy//blah:blah")
        self.assertEqual("@poppy//blah", n1.canonical_form)

    def test_str(self):
        n1 = label.Label("@poppy//blah:blah")
        self.assertEqual("@poppy//blah", str(n1))

    def test_with_target(self):
        n1 = label.Label("@poppy//b22")
        self.assertEqual("@poppy//b22:foo",
                         n1.with_target("foo").canonical_form)
        
        n1 = label.Label("@poppy//b22:b22")
        self.assertEqual("@poppy//b22:foo",
                         n1.with_target("foo").canonical_form)

        n1 = label.Label("@poppy//b22:blah")
        self.assertEqual("@poppy//b22:foo",
                         n1.with_target("foo").canonical_form)


if __name__ == '__main__':
    unittest.main()

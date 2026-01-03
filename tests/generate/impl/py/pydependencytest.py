import unittest

import generate.impl.py.pydependency as pydependency


class PyDependencyTest(unittest.TestCase):

    def test_native_repr(self):
        dep = pydependency.PyDependency("mydep", "1.2.3")
        self.assertEqual(dep.native_repr, "mydep>=1.2.3")

        dep = pydependency.PyDependency("mydep", "1.2.3", extras=["ext"])
        self.assertEqual(dep.native_repr, "mydep[ext]>=1.2.3")


if __name__ == '__main__':
    unittest.main()

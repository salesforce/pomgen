"""
Copyright (c) 2023, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import code
import unittest


class CodeTest(unittest.TestCase):

    def test_get_function_block(self):
        content = """
foo
blah
f1(
  a = 1,
  b = 2
)
goo
zoo
f2(
  c = 3,
  d = 4,
)
shoe
"""

        self.assertEqual(code.get_function_block(content, "f1").strip(), """
f1(
  a = 1,
  b = 2
)
""".strip())
        self.assertEqual(code.get_function_block(content, "f2").strip(), """
f2(
  c = 3,
  d = 4,
)
""".strip())


    def test_get_attr_value(self):
        content = """
a = "string",
b = True,
c = ["a", "b", "c"]
something = else
"""
        self.assertEqual("string", code.get_attr_value("a", str, None, content))
        self.assertEqual(True, code.get_attr_value("b", bool, None, content))
        self.assertEqual(["a", "b", "c"], code.get_attr_value("c", list, None, content))
        

if __name__ == '__main__':
    unittest.main()

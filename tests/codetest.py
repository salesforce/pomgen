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


    def test_parse_attributes(self):
        content = """
foo(
    a_string = "my = string",
    bool_True = True,
    bool_False  = False,
    an_int =   68,
    a_list =  ["a", "b", "c"],
    a_dict = {"one":  2},
    a_tuple = (1, 2, "sn")
)
"""
        self.assertEqual({"a_string": "my = string",
                          "bool_True": True,
                          "bool_False": False,
                          "an_int": 68,
                          "a_list": ["a", "b", "c"],
                          "a_dict": {"one": 2},
                          "a_tuple": (1, 2, "sn")},
                         code.parse_attributes(content))

    def test_parse_attributes__linebreaks(self):
        content = """
foo(
    a_list =  [
   "something"   ,  "here",
   "is",
   "[GOING ON]",
   ],
   a_string = "forever",
)
"""
        self.assertEqual({"a_string": "forever",
                          "a_list": ["something", "here", "is", "[GOING ON]"]},
                         code.parse_attributes(content))
        

if __name__ == '__main__':
    unittest.main()

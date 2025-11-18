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

    def test_get_function_block__substring_match(self):
        content = """
foo
blah
maven_artifact_update(
  a = 1,
  b = 2
)
"""

        self.assertIsNone(code.get_function_block(content, "artifact"))

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
        attributes, _ = code.parse_attributes(content)
        self.assertEqual({"a_string": "my = string",
                          "bool_True": True,
                          "bool_False": False,
                          "an_int": 68,
                          "a_list": ["a", "b", "c"],
                          "a_dict": {"one": 2},
                          "a_tuple": (1, 2, "sn")},
                          attributes)

    def test_indexes__with_comma(self):
        content = """
# foo

java_binary(
    name   =   "test",
    flaky  = True,
    place = "Atlanta"
)
"""
        _, value_indexes = code.parse_attributes(content)
        start, end = value_indexes["flaky"]

        updated_content = content[:start] + "False" + content[end+1:]

        self.assertEqual("""
# foo

java_binary(
    name   =   "test",
    flaky  = False,
    place = "Atlanta"
)
""", updated_content)

    def test_indexes__with_space_after(self):
        content = """
java_binary(
    name   =   "test",
    flaky  = True  ,
    place = "Atlanta"
)
"""
        _, value_indexes = code.parse_attributes(content)
        start, end = value_indexes["flaky"]

        updated_content = content[:start] + "False" + content[end+1:]

        self.assertEqual("""
java_binary(
    name   =   "test",
    flaky  = False  ,
    place = "Atlanta"
)
""", updated_content)


    def test_indexes__without_comma(self):
        content = """
java_binary(
    name   =   "test",
    flaky=  True
)
"""
        _, value_indexes = code.parse_attributes(content)
        start, end = value_indexes["flaky"]

        updated_content = content[:start] + "False" + content[end+1:]

        self.assertEqual("""
java_binary(
    name   =   "test",
    flaky=  False
)
""", updated_content)

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
        attributes, _ = code.parse_attributes(content)
        self.assertEqual({"a_string": "forever",
                          "a_list": ["something", "here", "is", "[GOING ON]"]},
                         attributes)
        
    def test_parse_artifact_attributes__artifact(self):
        content = """
# def:
artifact(
    name = "LAX",
)
# update:
artifact_update(
    strat = "guitar",
)
"""
        _, value_indexes = code.parse_artifact_attributes(content)
        start, end = value_indexes["name"]

        updated_content = content[:start] + '"NRT"' + content[end+1:]

        self.assertEqual("""
# def:
artifact(
    name = "NRT",
)
# update:
artifact_update(
    strat = "guitar",
)
""", updated_content)

    def test_parse_artifact_attributes__artifact_update(self):
        content = """
# def:
artifact(
    name = "LAX",
)
# update:
artifact_update(
    strat = "guitar",
)
"""
        _, value_indexes = code.parse_artifact_attributes(content)
        start, end = value_indexes["strat"]

        updated_content = content[:start] + '"tocaster"' + content[end+1:]

        self.assertEqual("""
# def:
artifact(
    name = "LAX",
)
# update:
artifact_update(
    strat = "tocaster",
)
""", updated_content)


if __name__ == '__main__':
    unittest.main()

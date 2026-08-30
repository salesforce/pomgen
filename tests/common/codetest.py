"""
Copyright (c) 2023, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import common.code as code
import os
import unittest
import unittest.mock as mock


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


    def test_parse_artifact_attributes__expr(self):
        content = """
# def:
artifact(
    name = "LAX",
    artifact_id = "1 if 1==2 else 2",
)
# update:
artifact_update(
    strat = "guitar",
)
"""
        attrs, _ = code.parse_artifact_attributes(content)

        self.assertEqual(2, attrs["artifact_id"])


    def test_parse_artifact_attributes__artifact_update_with_expr(self):
        content = """
# def:
artifact(
    name = "LAX",
    artifact_id = "1 if 1==2 else 2",
)
# update:
artifact_update(
    strat = "guitar",
)
"""
        attrs, value_indexes = code.parse_artifact_attributes(content)
        self.assertEqual(2, attrs["artifact_id"]) # evaluated

        start, end = value_indexes["strat"]

        # indexes use literal expression, not the evaluated expr
        updated_content = content[:start] + '"tocaster"' + content[end+1:]

        self.assertEqual("""
# def:
artifact(
    name = "LAX",
    artifact_id = "1 if 1==2 else 2",
)
# update:
artifact_update(
    strat = "tocaster",
)
""", updated_content)
        

    def test_parse_as_expr(self):
        self.assertEqual("foo", code.parse_as_expr("foo"))
        self.assertEqual("foo", code.parse_as_expr("'foo'"))
        self.assertEqual(3, code.parse_as_expr("3 if 1==1 else 2"))
        self.assertEqual(2, code.parse_as_expr("3 if 1== 2 else 2"))
        self.assertEqual("foo", code.parse_as_expr("foo if 2 == 2 else 2"))
        self.assertEqual("foo", code.parse_as_expr("'foo' if 2 == 2 else 2"))
        self.assertEqual("foo", code.parse_as_expr("2 if 2 == 1 else foo"))
        self.assertEqual("foo", code.parse_as_expr("2 if 2 == 1 else 'foo'"))

    @mock.patch.dict(os.environ, {"FOO22": "some_value"})
    def test_parse_as_expr__env_var_lhs(self):
        self.assertEqual(3, code.parse_as_expr("3 if '$FOO22'=='some_value' else 2"))

    @mock.patch.dict(os.environ, {"FOSTER": "Dublin"})
    def test_parse_as_expr__env_var_rhs(self):
        self.assertEqual(3, code.parse_as_expr("3 if 'Dublin' == '$FOSTER' else 2"))

    def test_parse_as_expr__env_var_not_set(self):
        # FOO22 is not set, so it evals to ''
        self.assertEqual(3, code.parse_as_expr("3 if '$FOO22'=='' else 2"))

    def test_parse_as_expr__no_func_calls_allowed(self):
        try:
            code.parse_as_expr("sys.exit()")
            self.fail("Expected exception")
        except code.BadCodeException:
            pass
        except Exception:
            self.fail("Expected BadCodeException")            

        try:
            code.parse_as_expr("1 if 1==1 else sys.exit()")
            self.fail("Expected exception")
        except code.BadCodeException:
            pass
        except Exception:
            self.fail("Expected BadCodeException")            

        try:
            code.parse_as_expr("sys.exit() if 1==1 else 2")
            self.fail("Expected exception")
        except code.BadCodeException:
            pass
        except Exception:
            self.fail("Expected BadCodeException")            


if __name__ == '__main__':
    unittest.main()

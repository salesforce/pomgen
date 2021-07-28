"""
Copyright (c) 2021, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import unittest
from common import instancequery


class InstanceQueryTest(unittest.TestCase):

    def test_query_instance1(self):
        class Foo:
            def __init__(self):
                self.prop = 1
        foo = Foo()

        matching_query = instancequery.InstanceQuery("prop=1")
        mismatching_query = instancequery.InstanceQuery("prop=2")

        self.assertIs(matching_query(foo), foo)
        self.assertIsNone(mismatching_query(foo))

    def test_query_instance2(self):
        class Foo:
            def __init__(self):
                self.prop1 = 1
                self.prop2 = 2
        foo = Foo()

        matching_query1 = instancequery.InstanceQuery("prop1=1 and prop2=2")
        matching_query2 = instancequery.InstanceQuery("prop2= 2 and prop1 =1")
        mismatching_query1 = instancequery.InstanceQuery("prop1=1 and prop2=4")
        mismatching_query2 = instancequery.InstanceQuery("prop3=1 and prop2=4")

        self.assertIs(matching_query1(foo), foo)
        self.assertIs(matching_query2(foo) ,foo)
        self.assertIsNone(mismatching_query1(foo))
        self.assertIsNone(mismatching_query2(foo))

    def test_query_instance_with_properties(self):
        class Foo:
            def __init__(self):
                self._prop = 1
            @property
            def prop(self):
                return self._prop
        foo = Foo()

        matching_query = instancequery.InstanceQuery("prop=1")

        self.assertIs(matching_query(foo), foo)

    def test_query_dict(self):
        d = {"prop1": 200}

        matching_query = instancequery.InstanceQuery("prop1=200")
        mismatching_query = instancequery.InstanceQuery("prop1=100")

        self.assertIs(matching_query(d), d)
        self.assertIsNone(mismatching_query(d))

    def test_query_many(self):
        d1 = {"prop1" : 100}
        d2 = {"prop1" : 200}
        d3 = {"prop1" : 300}
        d4 = {"prop1" : 100}

        matching_query = instancequery.InstanceQuery("prop1=100")

        self.assertEqual(matching_query([d1, d2, d3, d4]), [d1, d4])

    def test_query_empty_list(self):
        d1 = {"prop1" : [1, 2, 3]}
        d2 = {"prop1" : []}
        d3 = {"prop1" : ["foo"]}

        matching_query = instancequery.InstanceQuery("prop1 is empty")

        self.assertEqual(matching_query([d1, d2, d3]), [d2])

    def test_startswith(self):
        class Foo:
            def __init__(self):
                self.prop = "abc"
        foo = Foo()

        matching_query = instancequery.InstanceQuery("prop startswith ab")
        mismatching_query = instancequery.InstanceQuery("prop startswith de")

        self.assertIs(matching_query(foo), foo)
        self.assertIsNone(mismatching_query(foo))


if __name__ == '__main__':
    unittest.main()


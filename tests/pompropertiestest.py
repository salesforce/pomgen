from crawl import dependency
from crawl import pomproperties
from crawl import pomparser
import unittest

class PomPropertiesTest(unittest.TestCase):

    def test_get_group_version_dict__basic(self):
        guava_failureaccess = dependency.new_dep_from_maven_art_str("com.google.guava:failureaccess:1", "failureaccess")
        android_annotations = dependency.new_dep_from_maven_art_str("com.google.android:annotations:4", "annotations")
        expected_dict = {
            "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1"),
            "com.google.android":pomparser.ParsedProperty("com.google.android.version", "4"),
        }
        self.assertTrue(self._compare_group_version_dict(expected_dict, pomproperties.get_group_version_dict([guava_failureaccess, android_annotations])))

    def test_get_group_version_dict__same_group_same_version(self):
        guava_failureaccess = dependency.new_dep_from_maven_art_str("com.google.guava:failureaccess:1", "failureaccess")
        guava_guava = dependency.new_dep_from_maven_art_str("com.google.guava:guava:1", "guava")
        expected_dict = { "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1") }
        self.assertTrue(self._compare_group_version_dict(expected_dict, pomproperties.get_group_version_dict([guava_failureaccess, guava_guava])))

    def test_get_group_version_dict__same_group_same_version(self):
        guava_failureaccess = dependency.new_dep_from_maven_art_str("com.google.guava:failureaccess:1", "failureaccess")
        guava_guava = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20", "guava")
        expected_dict = { "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1") }
        self.assertTrue(self._compare_group_version_dict(expected_dict, pomproperties.get_group_version_dict([guava_failureaccess, guava_guava])))

    def test_get_group_version_dict__existing_dict(self):
        existing_dict = { "com.google.guava":pomparser.ParsedProperty("existing.guava.version", "20") }
        guava_failureaccess = dependency.new_dep_from_maven_art_str("com.google.guava:failureaccess:1", "failureaccess")
        expected_dict = { "com.google.guava":pomparser.ParsedProperty("existing.guava.version", "20") }
        self.assertTrue(self._compare_group_version_dict(expected_dict, pomproperties.get_group_version_dict([guava_failureaccess], existing_dict)))

    def test_gen_version_properties__basic(self):
        group_version_dict = {
            "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1")
        }
        expected_pom = "        <com.google.guava.version>1</com.google.guava.version>\n"
        self.assertEqual(expected_pom, pomproperties.gen_version_properties(group_version_dict))

    def test_gen_version_properties__sorted(self):
        group_version_dict = {
            "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1"),
            "com.google.android":pomparser.ParsedProperty("com.google.android.version", "4"),
        }
        expected_pom = """        <com.google.android.version>4</com.google.android.version>
        <com.google.guava.version>1</com.google.guava.version>
"""
        self.assertEqual(expected_pom, pomproperties.gen_version_properties(group_version_dict))

    def test_gen_version_properties__existing_property(self):
        group_version_dict = {
            "com.google.guava":pomparser.ParsedProperty("com.google.guava.version", "1"),
            "com.google.android":pomparser.ParsedProperty("com.google.android.version", "4"),
        }
        original_pom = """
    <project>
        <properties>
            <com.google.guava.version>1</com.google.guava.version>
        </properties>
    </project>
"""
        expected_pom = "        <com.google.android.version>4</com.google.android.version>\n"
        self.assertEqual(expected_pom, pomproperties.gen_version_properties(group_version_dict, original_pom))

    def _compare_group_version_dict(self, expected_dict, actual_dict):
        for group_id in expected_dict:
            if group_id not in actual_dict:
                return False
            else:
                if expected_dict[group_id].get_property_name() != actual_dict[group_id].get_property_name() or expected_dict[group_id].get_property_value() != actual_dict[group_id].get_property_value():
                    return False
        return True

if __name__ == '__main__':
    unittest.main()


"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import configvalueloader
import os
import tempfile
import unittest


class ConfigValueLoaderTest(unittest.TestCase):

    def test_load_jar_classifier__from_config(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[artifact]
jar_classifier=jdk8
""")

        values = configvalueloader.load_config_values(
            ["artifact.jar_classifier"], repo_root)

        self.assertEqual("jdk8", values["artifact.jar_classifier"])

    def test_load_jar_classifier__not_configured(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, "")

        values = configvalueloader.load_config_values(
            ["artifact.jar_classifier"], repo_root)

        self.assertIsNone(values["artifact.jar_classifier"])

    def test_load_pom_base_filename__from_config(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[general]
pom_base_filename=custom-pom
""")

        values = configvalueloader.load_config_values(
            ["general.pom_base_filename"], repo_root)

        self.assertEqual("custom-pom", values["general.pom_base_filename"])

    def test_load_pom_base_filename__default(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, "")

        values = configvalueloader.load_config_values(
            ["general.pom_base_filename"], repo_root)

        # The config module has its own default of "pom"
        self.assertEqual("pom", values["general.pom_base_filename"])

    def test_unknown_key(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, "")

        with self.assertRaises(ValueError) as ctx:
            configvalueloader.load_config_values(
                ["unknown.key"], repo_root)

        self.assertIn("Unknown config key [unknown.key]", str(ctx.exception))

    def test_load_multiple_values__both_configured(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[artifact]
jar_classifier=jdk11

[general]
pom_base_filename=my-pom
""")

        values = configvalueloader.load_config_values(
            ["artifact.jar_classifier", "general.pom_base_filename"], repo_root)

        self.assertEqual(2, len(values))
        self.assertEqual("jdk11", values["artifact.jar_classifier"])
        self.assertEqual("my-pom", values["general.pom_base_filename"])

    def test_output_format__tuple_style(self):
        """Test output is tuple-style with | separator for easy bash parsing."""
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[artifact]
jar_classifier=jdk17

[general]
pom_base_filename=custom-pom
""")

        keys = ["artifact.jar_classifier", "general.pom_base_filename"]
        values = configvalueloader.load_config_values(keys, repo_root)
        output = configvalueloader.format_output(keys, values, "|")

        # Verify output format
        self.assertEqual("jdk17|custom-pom", output)

        # Verify bash can parse it
        parts = output.split("|")
        self.assertEqual(2, len(parts))
        self.assertEqual("jdk17", parts[0])
        self.assertEqual("custom-pom", parts[1])

    def test_output_format__with_none_value(self):
        """Test output when a value is None."""
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[general]
pom_base_filename=my-pom
""")

        keys = ["artifact.jar_classifier", "general.pom_base_filename"]
        values = configvalueloader.load_config_values(keys, repo_root)
        output = configvalueloader.format_output(keys, values, "|")

        # Verify output format - None should be represented as string "None"
        self.assertEqual("None|my-pom", output)

        # Verify bash can parse it
        parts = output.split("|")
        self.assertEqual(2, len(parts))
        self.assertEqual("None", parts[0])
        self.assertEqual("my-pom", parts[1])

    def test_output_format__custom_separator(self):
        """Test output with custom separator."""
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[artifact]
jar_classifier=jdk17

[general]
pom_base_filename=custom-pom
""")

        keys = ["artifact.jar_classifier", "general.pom_base_filename"]
        values = configvalueloader.load_config_values(keys, repo_root)
        output = configvalueloader.format_output(keys, values, separator="|||")

        # Verify output format with custom separator
        self.assertEqual("jdk17|||custom-pom", output)

        # Verify bash can parse it with custom separator
        parts = output.split("|||")
        self.assertEqual(2, len(parts))
        self.assertEqual("jdk17", parts[0])
        self.assertEqual("custom-pom", parts[1])

    def test_load_multiple_values__one_not_configured(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, """
[general]
pom_base_filename=my-pom
""")

        values = configvalueloader.load_config_values(
            ["artifact.jar_classifier", "general.pom_base_filename"], repo_root)

        self.assertEqual(2, len(values))
        self.assertIsNone(values["artifact.jar_classifier"])
        self.assertEqual("my-pom", values["general.pom_base_filename"])

    def test_load_multiple_values__unknown_key(self):
        repo_root = tempfile.mkdtemp("root")
        self._setup_repo(repo_root, "")

        with self.assertRaises(ValueError) as ctx:
            configvalueloader.load_config_values(
                ["artifact.jar_classifier", "unknown.key"], repo_root)

        self.assertIn("Unknown config key [unknown.key]", str(ctx.exception))

    def _setup_repo(self, repo_root, poppyrc_content):
        """Sets up a minimal repository structure for testing."""
        # Create src/config directory
        os.makedirs(os.path.join(repo_root, "src/config"))

        # Create pom_template.xml
        pom_template_path = os.path.join(repo_root, "src/config/pom_template.xml")
        with open(pom_template_path, "w") as f:
            f.write("pom template content")

        # Create .poppyrc
        poppyrc_path = os.path.join(repo_root, ".poppyrc")
        with open(poppyrc_path, "w") as f:
            f.write(poppyrc_content)


if __name__ == '__main__':
    unittest.main()

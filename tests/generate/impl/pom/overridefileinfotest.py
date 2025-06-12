"""
Copyright (c) 2023, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import generate.impl.pom.overridefileinfo as overridefileinfo
import os
import tempfile
import unittest


class OverrideFileInfoTest(unittest.TestCase):

    def test_overridden_dep(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(
            repo_root,
            "override_file.bzl",
            """
overrides = {
    # JAVAX -> JAKARTA MIGRATION
    "javax.activation:activation":              "@jakarta//:jakarta_activation_jakarta_activation_api",
    "javax.inject:javax.inject":                "@jakarta//:jakarta_inject_jakarta_inject_api",

    # JSRs/early impls (these aren't perfect replacements, but better than using ancient stuff)
    "com.sun.activation:jakarta.activation":    "@jakarta//:jakarta_activation_jakarta_activation_api",
""")
        o = overridefileinfo.OverrideFileInfo(("override_file.bzl",), repo_root)

        self.assertEqual({
            'javax_activation_activation': '@jakarta//:jakarta_activation_jakarta_activation_api', 
            'javax_inject_javax_inject': '@jakarta//:jakarta_inject_jakarta_inject_api', 
            'com_sun_activation_jakarta_activation': '@jakarta//:jakarta_activation_jakarta_activation_api'
            }, o.label_to_overridden_fq_label)

    def test_json_file_not_found(self):
        with self.assertRaises(Exception) as ctx:
            overridefileinfo.OverrideFileInfo(("a/b/c", "d/e/f"), "/repo_root")

        self.assertIn("not found", str(ctx.exception))
        self.assertIn("/repo_root/a/b/c", str(ctx.exception))

    def _touch_file_at_path(self, repo_root_path, file_path, content):
        path = os.path.join(repo_root_path, file_path)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(content)


if __name__ == '__main__':
    unittest.main()

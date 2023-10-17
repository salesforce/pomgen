from common import overridefileinfo
import os
import tempfile
import unittest
from crawl import dependency

class OverrideFileInfoTest(unittest.TestCase):

    def test_json_file_not_found(self):
        m = overridefileinfo.OverrideFileInfo(("a/b/c", "d/e/f"), "/repo_root")
        
        with self.assertRaises(Exception) as ctx:
            m.get_override_file_names_and_paths()

        self.assertIn("not found", str(ctx.exception))
        self.assertIn("/repo_root/a/b/c", str(ctx.exception))

    def test_explicit_paths(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(
            repo_root,
            "override_file.bzl",
            '''
overrides = {
    # JAVAX -> JAKARTA MIGRATION
    "javax.activation:activation":              "@jakarta//:jakarta_activation_jakarta_activation_api",
    "javax.inject:javax.inject":                "@jakarta//:jakarta_inject_jakarta_inject_api",

    # JSRs/early impls (these aren't perfect replacements, but better than using ancient stuff)
    "com.sun.activation:jakarta.activation":    "@jakarta//:jakarta_activation_jakarta_activation_api",
'''
            )
        o = overridefileinfo.OverrideFileInfo(("override_file.bzl",), repo_root)

        files = o.get_override_file_names_and_paths()
        override_names_dict = o.name_to_override_dependencies()

        self.assertEqual(1, len(files))
        self.assertEqual("override_file", files[0][0])
        self.assertEqual(os.path.join(repo_root, "override_file.bzl"), files[0][1])
        self.assertEqual({
            'javax_activation_activation': '@jakarta//:jakarta_activation_jakarta_activation_api', 
            'javax_inject_javax_inject': '@jakarta//:jakarta_inject_jakarta_inject_api', 
            'com_sun_activation_jakarta_activation': '@jakarta//:jakarta_activation_jakarta_activation_api'
            }, override_names_dict)

    def test_overidden_dep_value(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(
            repo_root,
            "override_file.bzl",
            '''
overrides = {
    "javax.inject:javax.inject":                "@jakarta//:jakarta_inject_jakarta_inject_api",
'''
            )
        o = overridefileinfo.OverrideFileInfo(("override_file.bzl",), repo_root)

        artifact = "javax.inject:javax.inject:1"
        dep = dependency.new_dep_from_maven_art_str(artifact, "name")

        self.assertEqual("@jakarta//:jakarta_inject_jakarta_inject_api", o.overidden_dep_value(dep))

    def test_override_deps(self):
        repo_root = tempfile.mkdtemp("monorepo")
        self._touch_file_at_path(
            repo_root,
            "override_file.bzl",
            '''
overrides = {
    "javax.activation:activation":              "@jakarta//:jakarta_activation_jakarta_activation_api",
'''
            )
        ext_deps = {"@jakarta//:jakarta_activation_jakarta_activation_api": dependency.new_dep_from_maven_art_str("jakarta.activation:jakarta.activation-api:1.2.2", "name")}
        o = overridefileinfo.OverrideFileInfo(("override_file.bzl",), repo_root)

        artifacts = ["javax.activation:activation:1.1.1", "org.glassfish.hk2:hk2:2.6.1", "com.google.guava:guava:32.0.1-jre"]
        deps = [dependency.new_dep_from_maven_art_str(artifact, "name") for artifact in artifacts]

        overridden_deps = o.override_deps(deps, ext_deps)

        self.assertNotEqual(deps[0], overridden_deps[0])
        self.assertEqual(deps[1], overridden_deps[1])
        self.assertEqual(deps[2], overridden_deps[2])
        self.assertEqual(ext_deps["@jakarta//:jakarta_activation_jakarta_activation_api"], overridden_deps[0])

    def _touch_file_at_path(self, repo_root_path, file_path, content):
        path = os.path.join(repo_root_path, file_path)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with open(path, "w") as f:
            f.write(content)


if __name__ == '__main__':
    unittest.main()

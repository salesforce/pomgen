"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common.os_util import run_cmd
from common import maveninstallinfo
from config import config
from crawl import bazel
from crawl import dependency
import os
import unittest


class WorkspaceTest(unittest.TestCase):

    def setUp(self):
        self.orig_bazel_parse_maven_install = bazel.parse_maven_install
        f = dependency.new_dep_from_maven_art_str
        query_result = [
            (f("org.apache.maven:maven-artifact:3.3.9", "maven"), [],),
            (f("com.google.guava:guava:23.0", "maven"), [],),
            (f("ch.qos.logback:logback-classic:1.2.3", "maven"), [],)
        ]
        bazel.parse_maven_install = lambda names, paths, verbose: query_result
    
    def tearDown(self):
        bazel.parse_maven_install = self.orig_bazel_parse_maven_install


    def test_parse_maven_artifact_def(self):
        pass

    def test_filter_artifact_producing_packages(self):
        pass

    def _setup_repo(self, repo_root_path):
        run_cmd("git init .", cwd=repo_root_path)
        run_cmd("git config user.email 'test@example.com'", cwd=repo_root_path)
        run_cmd("git config user.name 'test example'", cwd=repo_root_path)
        self._commit(repo_root_path)

    def _commit(self, repo_root_path):
        run_cmd("git add .", cwd=repo_root_path)
        run_cmd("git commit -m 'test commit'", cwd=repo_root_path)

    def _touch_file_at_path(self, repo_root_path, package_rel_path, within_package_rel_path, filename):
        path = os.path.join(repo_root_path, package_rel_path, within_package_rel_path, filename)
        if os.path.exists(path):
            with open(path, "r+") as f:
                content = f.read()
                content += "abc\n"
                f.seek(0)
                f.write(content)
                f.truncate()
        else:
            parent_dir = os.path.dirname(path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(path, "w") as f:
                f.write("abc\n")

    def _write_build_pom(self, repo_root_path, package_rel_path, artifact_id, group_id, version):
        build_pom = """
maven_artifact(
    artifact_id = "%s",
    group_id = "%s",
    version = "%s",
    pom_generation_mode = "dynamic",
)

maven_artifact_update(
    version_increment_strategy = "minor",
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom"), "w") as f:
           f.write(build_pom % (artifact_id, group_id, version))

    def _write_build_pom_released(self, repo_root_path, package_rel_path, released_version, released_artifact_hash):
        build_pom_released = """
released_maven_artifact(
    version = "%s",
    artifact_hash = "%s",
)
"""
        path = os.path.join(repo_root_path, package_rel_path, "MVN-INF")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, "BUILD.pom.released"), "w") as f:
           f.write(build_pom_released % (released_version, released_artifact_hash))

    def _mocked_mvn_install_info(self, maven_install_name):
        mii = maveninstallinfo.MavenInstallInfo(())
        mii.get_maven_install_names_and_paths = lambda r: [(maven_install_name, "some/repo/path",)]
        return mii

    def _write_build_file(self, repo_root_path, package_rel_path, neverlink_attr_enabled = False):
        build_file = """
java_plugin(
    name = "lombok-plugin",
    generates_api = True,
    processor_class = "lombok.launch.AnnotationProcessorHider$AnnotationProcessor",
    visibility = ["//visibility:private"],
    deps = ["@nexus//:org_projectlombok_lombok"],
)

java_library(
    name = "lombok",
    neverlink = %s,
    exports = ["@nexus//:org_projectlombok_lombok"],
    exported_plugins = [":lombok-plugin"],
    visibility = ["//visibility:public"],
)
""" % (0 if not neverlink_attr_enabled else 1)

        path = os.path.join(repo_root_path, package_rel_path)
        if not os.path.exists(path):
            os.makedirs(path)
        build_file_path = os.path.join(path, "BUILD")
        with open(build_file_path, "w") as f:
           f.write(build_file)

    def _write_basic_workspace_file(self, repo_root_path):
        workspace_file = """
workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "4.1"
RULES_JVM_EXTERNAL_SHA = "f36441aa876c4f6427bfb2d1f2d723b48e9d930b62662bf723ddfb8fc80f0140"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
    url = "https://github.com/bazelbuild/rules_jvm_external/archive/%s.zip" % RULES_JVM_EXTERNAL_TAG,
)

load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven")


load("@rules_jvm_external//:repositories.bzl", "rules_jvm_external_deps")
rules_jvm_external_deps()
load("@rules_jvm_external//:setup.bzl", "rules_jvm_external_setup")
rules_jvm_external_setup()
"""
        path = os.path.join(repo_root_path)
        if not os.path.exists(path):
            os.makedirs(path)
        workspace_file_path = os.path.join(path, "WORKSPACE")
        with open(workspace_file_path, "w") as f:
           f.write(workspace_file)

    def _get_config(self, **kwargs):
        return config.Config(**kwargs)


if __name__ == '__main__':
    unittest.main()

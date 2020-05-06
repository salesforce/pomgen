"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

python_version = 'PY3'

py_binary(
    name = "pomgen",
    srcs = [":pomgen_files"],
    python_version = python_version,
)

py_binary(
    name = "query",
    main = "query_maven_metadata.py",
    srcs = [":pomgen_files"],
    python_version = python_version,
)

py_binary(
    name = "update",
    main = "update_maven_metadata.py",
    srcs = [":pomgen_files"],
    python_version = python_version,
)

filegroup(
    name = "pomgen_files",
    srcs = glob(["*.py",
                 "common/*.py",
                 "config/*.py",
                 "common/*.py",
                 "crawl/*.py"]),
    visibility = ["//misc:__subpackages__",],
)


# small tests

py_test(
    name = "argsupporttest",
    srcs = ["common/argsupport.py",
            "common/mdfiles.py",
            "common/logger.py",
            "crawl/bazel.py",
            "common/os_util.py",
            "tests/argsupporttest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "artifactprocessortest",
    srcs = ["common/code.py",
            "common/logger.py",
            "common/mdfiles.py",
            "common/os_util.py",
            "common/pomgenmode.py",
            "common/version.py",
            "config/exclusions.py",
            "crawl/artifactprocessor.py",
            "crawl/buildpom.py",
            "crawl/git.py",
            "crawl/releasereason.py",
            "tests/artifactprocessortest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "bazeltest",
    srcs = ["common/mdfiles.py",
            "crawl/bazel.py", 
            "common/os_util.py",
            "tests/bazeltest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "buildpomtest",
    srcs = ["common/code.py",
            "common/mdfiles.py",
            "common/pomgenmode.py",
            "common/version.py",
            "crawl/buildpom.py",
            "tests/buildpomtest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "buildpomupdatetest",
    srcs = ["common/code.py",
            "common/mdfiles.py",
            "common/pomgenmode.py",
            "common/version.py",
            "config/exclusions.py",
            "crawl/git.py",
            "common/os_util.py",
            "tests/buildpomupdatetest.py",
            "update/buildpomupdate.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "configtest",
    srcs = ["common/logger.py",
            "config/config.py",
            "config/exclusions.py",
            "tests/configtest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "crawlertest",
    srcs = [":pomgen_files", "tests/crawlertest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "dependencytest",
    srcs = ["common/code.py", 
            "common/logger.py",
            "common/mdfiles.py",
            "common/pomgenmode.py",
            "common/version.py",
            "crawl/buildpom.py",
            "crawl/dependency.py",
            "tests/dependencytest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "libaggregatortest",
    srcs = ["common/code.py",
            "common/logger.py",
            "common/mdfiles.py",
            "common/pomgenmode.py",
            "common/version.py",
            "crawl/artifactprocessor.py",
            "crawl/git.py",
            "crawl/workspace.py",
            "crawl/bazel.py",
            "crawl/buildpom.py",
            "crawl/crawler.py",
            "crawl/dependency.py",
            "crawl/pom.py",
            "crawl/pomparser.py",
            "crawl/libaggregator.py",
            "crawl/releasereason.py",
            "common/os_util.py",
            "tests/libaggregatortest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "mdfilestest",
    srcs = ["common/mdfiles.py", "tests/mdfilestest.py",],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "pomgentest",
    srcs = [":pomgen_files", "tests/pomgentest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "pomtest",
    srcs = ["common/code.py",
            "common/logger.py",
            "common/mdfiles.py",
            "common/os_util.py",
            "common/pomgenmode.py",
            "common/version.py",
            "config/exclusions.py",
            "crawl/artifactprocessor.py",
            "crawl/bazel.py",
            "crawl/buildpom.py",
            "crawl/dependency.py",
            "crawl/git.py",
            "crawl/pom.py",
            "crawl/pomparser.py",
            "crawl/releasereason.py",
            "crawl/workspace.py",
            "tests/pomtest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "pomparsertest",
    srcs = ["common/logger.py",
            "crawl/dependency.py", 
            "crawl/pomparser.py", 
            "tests/pomparsertest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "workspacetest",
    srcs = ["common/code.py",
            "common/logger.py",
            "common/mdfiles.py",
            "common/os_util.py",
            "common/pomgenmode.py",
            "common/version.py",
            "config/exclusions.py",
            "crawl/artifactprocessor.py",
            "crawl/buildpom.py",
            "crawl/dependency.py",
            "crawl/git.py",
            "crawl/releasereason.py",
            "crawl/workspace.py",
            "tests/workspacetest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

py_test(
    name = "versiontest",
    srcs = ["common/code.py", "common/version.py", "tests/versiontest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)

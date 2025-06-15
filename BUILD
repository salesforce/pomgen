"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")


py_library(
    name = "pomgen_lib",
    srcs = glob(["src/pomgen.py",
                 "src/pomupdate/*.py",
                 "src/common/*.py",
                 "src/config/*.py",
                 "src/common/*.py",
                 "src/crawl/*.py",
                 "src/generate/*.py",
                 "src/generate/impl/*.py",
                 "src/generate/impl/pom/*.py",
                 "src/generate/impl/py/*.py"]),
    data = ["examples/java/pom_template.xml"],
    deps = ["@pip//lxml"],
    visibility = ["@poppy//:__subpackages__",],
)


# we will rename pomgen to gen
alias(
    name = "gen",
    actual = ":pomgen"
)

py_binary(
    name = "pomgen",
    srcs = ["src/pomgen.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
)

py_binary(
    name = "query",
    srcs = ["src/query.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
)

py_binary(
    name = "update",
    srcs = ["src/update.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
)


# bazel run //:pip.update
compile_pip_requirements(
    name = "pip",
    src = "//tools/pip:requirements.in",
    requirements_txt = "//tools/pip:requirements_lock.txt",
)

# bazel run //:examples_pip.update
compile_pip_requirements(
    name = "examples_pip",
    src = "//examples/python/pip:requirements.in",
    requirements_txt = "//examples/python/pip:requirements_lock.txt",
)

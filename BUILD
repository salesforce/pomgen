"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")


py_library(
    name = "pomgen_lib",
    srcs = glob(["src/pomupdate/*.py",
                 "src/common/*.py",
                 "src/config/*.py",
                 "src/common/*.py",
                 "src/crawl/*.py",
                 "src/generate/*.py",
                 "src/generate/impl/*.py",
                 "src/generate/impl/py/*.py"]),
    data = ["src/config/pom_template.xml"],
    deps = ["@pip//lxml"],
    visibility = ["//misc:__pkg__",],
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



py_test(
    name = "argsupporttest",
    srcs = ["tests/argsupporttest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "artifactprocessortest",
    srcs = ["tests/artifactprocessortest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "bazeltest",
    srcs = ["tests/bazeltest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "buildpomtest",
    srcs = ["tests/buildpomtest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "buildpomupdatetest",
    srcs = ["tests/buildpomupdatetest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "codetest",
    srcs = ["tests/codetest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "configtest",
    srcs = ["tests/configtest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "crawlertest",
    srcs = ["tests/crawlertest.py"],
    deps = [":pomgen_lib"],    
    imports = ["src"],
    size = "small",
)

py_test(
    name = "crawlerunittest",
    srcs = ["tests/crawlerunittest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "crawlertest_misc",
    srcs = ["tests/crawlertest_misc.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "dependencytest",
    srcs = ["tests/dependencytest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "dependencymdtest",
    srcs = ["tests/dependencymdtest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "instancequerytest",
    srcs = ["tests/instancequerytest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "labeltest",
    srcs = ["tests/labeltest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "libaggregatortest",
    srcs = ["tests/libaggregatortest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "maveninstallinfotest",
    srcs = ["tests/maveninstallinfotest.py",],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "overridefileinfotest",
    srcs = ["tests/overridefileinfotest.py",],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "mdfilestest",
    srcs = ["tests/mdfilestest.py",],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "pomgentest",
    srcs = ["src/pomgen.py", "tests/pomgentest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "pomgenerationstrategytest",
    srcs = ["tests/generate/impl/pomgenerationstrategytest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "pomtest",
    srcs = ["tests/pomtest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "pomparsertest",
    srcs = ["tests/pomparsertest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "requirementsparsertest",
    srcs = ["tests/generate/impl/py/requirementsparsertest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "workspacetest",
    srcs = ["tests/workspacetest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "versiontest",
    srcs = ["tests/versiontest.py"],
    deps = [":pomgen_lib"],
    imports = ["src"],
    size = "small",
)

py_test(
    name = "version_increment_strategy_test",
    srcs = ["tests/version_increment_strategy_test.py"],
    deps = [":pomgen_lib"],            
    imports = ["src"],
    size = "small",
)

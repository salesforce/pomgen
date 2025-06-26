load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "calculator",
    srcs = ["calculator.py",],
    deps = ["@examples_pip//boto3",], # not used, example 3rd party dependency
    visibility = [
        "//examples/python/111/src:__pkg__",
        "//examples/python/111:__pkg__"
    ],
)

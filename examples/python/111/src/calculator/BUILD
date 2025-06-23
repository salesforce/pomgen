load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "calculator",
    srcs = ["calculator.py",],
    # not actually used, just an example 3rd party dependency:
    deps = ["@examples_pip//boto3",],
    visibility = [
        "//examples/python/111/src:__pkg__",
        "//examples/python/111:__pkg__"
    ],
)

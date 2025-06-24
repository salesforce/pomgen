load("@aspect_rules_py//py:defs.bzl", "py_library", "py_binary")

py_library(
    name = "hello-world",
    srcs = ["hello.py",],
    visibility = ["//visibility:public",],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [":hello-world"],
    imports = ["."],
)

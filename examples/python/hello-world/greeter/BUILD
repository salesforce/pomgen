load("@aspect_rules_py//py:defs.bzl", "py_library", "py_binary")


py_library(
    name = "greeter",
    srcs = ["src/greeter/greeter.py",],
    deps = ["//examples/python/hello-world/computer"],
    imports = ["src"],
)

py_binary(
    name = "main",
    srcs = ["src/greeter/main.py"],
    deps = [":greeter"],
)

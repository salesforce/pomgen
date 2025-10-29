load("@aspect_rules_py//py:defs.bzl", "py_library", "py_binary")


py_library(
    name = "computer",
    srcs = ["src/computer/computer.py",],
    imports = ["src"],
    deps = ["@examples_pip//uvicorn",], # example dependency, not used
    visibility = ["//examples/python/hello-world/greeter:__pkg__"],
)

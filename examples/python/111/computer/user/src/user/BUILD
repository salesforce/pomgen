load("@aspect_rules_py//py:defs.bzl", "py_binary")


py_binary(
    name = "user",
    srcs = ["main.py",],
    deps = ["//examples/python/111/computer/amiga/src/amiga",],
    visibility = [
        "//examples/python/111/computer/user:__pkg__",
    ],
)

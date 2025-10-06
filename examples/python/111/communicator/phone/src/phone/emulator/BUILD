load("@aspect_rules_py//py:defs.bzl", "py_library")


py_library(
    name = "emulator",
    srcs = ["emulator.py",],
    deps = ["//examples/python/111/computer/amiga/src/amiga",],
    visibility = [
        "//examples/python/111/communicator/phone:__pkg__",
        "//examples/python/111/communicator/phone/src/phone:__pkg__",
    ],
)

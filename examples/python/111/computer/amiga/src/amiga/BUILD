load("@aspect_rules_py//py:defs.bzl", "py_library")


py_library(
    name = "amiga",
    srcs = ["startup.py",],
    deps = ["//examples/python/111/computer/amiga/src/amiga/workbench"],
    visibility = [
        "//examples/python/111/communicator/phone/src/phone/emulator:__pkg__",
        "//examples/python/111/computer/amiga:__pkg__",
        "//examples/python/111/computer/user/src/user:__pkg__"
    ],
    imports = ["."],
)

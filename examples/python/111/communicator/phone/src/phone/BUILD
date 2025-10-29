load("@aspect_rules_py//py:defs.bzl", "py_library")


py_library(
    name = "phone",
    srcs = ["mobile.py",],
    deps = [
        "//examples/python/111/communicator/phone/src/phone/emulator",
        "//examples/python/111/communicator/phone/src/phone/message",
        "//examples/python/111/communicator/phone/src/phone/ringtone"
    ],
    visibility = [
        "//examples/python/111/communicator/caller:__pkg__",    
        "//examples/python/111/communicator/phone:__pkg__",
    ],
    imports = ["."],
)

load("@aspect_rules_py//py:defs.bzl", "py_venv")


py_venv(
    name = "venv",
    testonly = True,
    deps = [
        "//examples/python/111/communicator/phone/src/phone",
        "//examples/python/111/communicator/phone/src/phone/emulator",
        "//examples/python/111/communicator/phone/src/phone/message",
        "//examples/python/111/communicator/phone/src/phone/ringtone",
        "//examples/python/111/communicator/phone/tests",
    ],
)


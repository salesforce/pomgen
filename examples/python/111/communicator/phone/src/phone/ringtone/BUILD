load("@aspect_rules_py//py:defs.bzl", "py_library")


py_library(
    name = "ringtone",
    srcs = ["ringtone.py",],
    deps = ["@examples_pip//uvicorn",], # example dependency, not used
    visibility = [
        "//examples/python/111/communicator/phone:__pkg__",
        "//examples/python/111/communicator/phone/src/phone:__pkg__",
    ],
)

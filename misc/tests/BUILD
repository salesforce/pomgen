load("@aspect_rules_py//py:defs.bzl", "py_test")


py_test(
    name = "extdeps_pomgentest",
    srcs = ["extdeps_pomgentest.py"],
    deps = [
        "//:poppy_lib",
        "//misc:extdeps_pomgen_lib",
    ],
    size = "small",
)

py_test(
    name = "configvalueloadertest",
    srcs = ["configvalueloadertest.py"],
    deps = [
        "//:poppy_lib",
        "//misc:configvalueloader_lib",
    ],
    size = "small",
)

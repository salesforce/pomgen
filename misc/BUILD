load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_test")


py_binary(
    name = "extdeps",
    srcs = ["extdeps_pomgen.py"],
    main = "extdeps_pomgen.py",
    deps = ["//:pomgen_lib"],
    imports = ["../src"],
)

py_binary(
    name = "configvalueloader",
    srcs = ["configvalueloader.py"],
    deps = ["//:pomgen_lib"],
    imports = ["../src"],
)

py_test(
    name = "extdeps_pomgentest",
    srcs = ["extdeps_pomgen.py",
            "tests/extdeps_pomgentest.py"],
    deps = ["//:pomgen_lib"],
    imports = [".", "../src"],
    size = "small",
)


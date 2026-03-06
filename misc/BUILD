load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")


py_library(
    name = "extdeps_pomgen_lib",
    srcs = ["extdeps_pomgen.py"],
    deps = ["//:poppy_lib"],
    imports = ["../src", "."],
    visibility = ["//misc/tests:__pkg__"],
)

py_binary(
    name = "extdeps",
    main = "extdeps_pomgen.py",
    srcs = ["extdeps_pomgen.py"],
    deps = [":extdeps_pomgen_lib"],
    imports = ["../src"],
)

py_library(
    name = "configvalueloader_lib",
    srcs = ["configvalueloader.py"],
    deps = ["//:poppy_lib"],
    imports = ["../src", "."],
    visibility = ["//misc/tests:__pkg__"],
)

py_binary(
    name = "configvalueloader",
    srcs = ["configvalueloader.py"],
    deps = ["//:poppy_lib"],
    imports = ["../src"],
)


python_version = 'PY3'

py_binary(
    name = "extdeps",
    srcs = ["extdeps_pomgen.py"],
    main = "extdeps_pomgen.py",
    deps = ["//:pomgen_lib"],
    imports = ["../src"],
    python_version = python_version,
)

py_binary(
    name = "configvalueloader",
    srcs = ["configvalueloader.py"],
    deps = ["//:pomgen_lib"],
    imports = ["../src"],
    python_version = python_version,
)

py_test(
    name = "extdeps_pomgentest",
    srcs = ["extdeps_pomgen.py",
            "tests/extdeps_pomgentest.py"],
    deps = ["//:pomgen_lib"],
    imports = [".", "../src"],
    size = "small",
    python_version = python_version,
)


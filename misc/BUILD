python_version = 'PY3'

py_binary(
    name = "extdeps",
    srcs = ["//:pomgen_files", "extdeps_pomgen.py"],
    main = "extdeps_pomgen.py",
    python_version = python_version,
)

py_test(
    name = "extdeps_pomgentest",
    srcs = ["//:pomgen_files",
            "extdeps_pomgen.py",
            "tests/extdeps_pomgentest.py"],
    imports = ["."],
    size = "small",
    python_version = python_version,
)


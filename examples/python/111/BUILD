load("@aspect_rules_py//py:defs.bzl", "py_venv")


alias(
    name = "111",
    actual = "//examples/python/111/src:main"
)


py_venv(
    name = "venv",
    testonly = True,
    deps = [
        "//examples/python/111/src:hello-world",
        "//examples/python/111/src/calculator:calculator",
    ],
)


load("@aspect_rules_py//py:defs.bzl", "py_venv")


alias(
    name = "user",
    actual = "//examples/python/111/computer/user/src/user",
)

py_venv(
    name = "venv",
    deps = [
        "//examples/python/111/computer/user/src/user",
    ],
)


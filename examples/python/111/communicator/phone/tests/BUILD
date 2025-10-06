load("@aspect_rules_py//py:defs.bzl", "py_test",)

py_test(
    name = "tests",
    srcs = ["test.py",],
    deps = ["@examples_pip//fastapi"], # test dep, NOT added to pyproject.toml
    visibility = ["//examples/python/111/communicator/phone:__pkg__"],
)

load("@aspect_rules_py//py:defs.bzl", "py_test")


[py_test(
    name = name[:-len(".py")],
    srcs = [name],
    deps = ["//:pomgen_lib"],
    imports = ["../src"],
    size = "small",
) for name in glob(["*.py"],)]

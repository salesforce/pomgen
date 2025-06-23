load("@aspect_rules_py//py:defs.bzl", "py_library", "py_binary")

py_library(
    name = "hello-world",
    srcs = ["hello.py",],
    deps = ["@examples_pip//uvicorn", # not used, example 3rd party dependency
            "//examples/python/111/src/calculator",
            #"//examples/python/empty/src:hello-world",
    ],
    visibility = ["//examples/python/111:__pkg__",],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [":hello-world"],
    imports = ["."],
    visibility = ["//examples/python/111:__pkg__",],
)

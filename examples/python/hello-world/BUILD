load("@aspect_rules_py//py:defs.bzl", "py_library", "py_binary")

py_library(
    name = "hello-world",
    srcs = ["src/hello.py",],
    deps = ["@examples_pip//boto3",
            "@examples_pip//fastapi",
            "@examples_pip//uvicorn"],
)

py_binary(
    name = "main",
    srcs = ["src/main.py"],
    deps = [":hello-world"],
    imports = ["src"],
)

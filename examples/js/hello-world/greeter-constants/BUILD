load("@aspect_rules_js//npm:defs.bzl", "npm_package")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")

ts_project(
    name = "greeter-constants",
    srcs = ["src/constants.ts"],
    declaration = True,
    transpiler = "tsc",
    tsconfig = "tsconfig.json",
    visibility = ["//examples/js/hello-world/greeter-lib:__pkg__"],
)

npm_package(
    name = "pkg",
    srcs = [
        ":greeter-constants",
        "package.json",
    ],
    package = "greeter-constants",
    visibility = ["//visibility:public"],
)

load("@aspect_rules_js//js:defs.bzl", "js_binary")
load("@aspect_rules_js//npm:defs.bzl", "npm_package")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@npm//:defs.bzl", "npm_link_all_packages")

npm_link_all_packages(name = "node_modules")

ts_project(
    name = "greeter",
    srcs = ["src/index.ts"],
    tsconfig = "tsconfig.json",
    transpiler = "tsc",
    deps = [
        "//examples/js/hello-world/greeter-lib",
    ],
)

npm_package(
    name = "pkg",
    srcs = [
        ":greeter",
        "package.json",
    ],
    package = "greeter",
    visibility = ["//visibility:public"],
)

js_binary(
    name = "greeter_bin",
    entry_point = "src/index.js",
    data = [
        ":greeter",
        ":node_modules/greeter-lib",
    ],
)

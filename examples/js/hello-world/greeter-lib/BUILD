load("@aspect_rules_js//npm:defs.bzl", "npm_package")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@npm//:defs.bzl", "npm_link_all_packages")

npm_link_all_packages(name = "node_modules")

ts_project(
    name = "greeter-lib",
    srcs = [
        "src/greeter.ts",
        "src/greetingbuilder.ts",
    ],
    declaration = True,
    transpiler = "tsc",
    tsconfig = "tsconfig.json",
    visibility = ["//examples/js/hello-world/greeter:__pkg__"],
    deps = [
        "//examples/js:node_modules/figlet",
        "//examples/js:node_modules/@types/figlet",
        "//examples/js/hello-world/greeter-constants",
    ],
)

npm_package(
    name = "pkg",
    srcs = [
        ":greeter-lib",
        "package.json",
    ],
    package = "greeter-lib",
    visibility = ["//visibility:public"],
)

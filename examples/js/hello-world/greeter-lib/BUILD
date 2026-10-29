load("@aspect_rules_js//js:defs.bzl", "js_test")
load("@aspect_rules_js//npm:defs.bzl", "npm_package")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@npm//:defs.bzl", "npm_link_all_packages")

npm_link_all_packages(name = "node_modules")

ts_project(
    name = "greeter-lib_project",
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

ts_project(
    name = "greeter-lib_test_lib",
    srcs = ["tests/greetingbuilder.test.ts"],
    declaration = True,
    testonly = True,
    transpiler = "tsc",
    tsconfig = "tsconfig.json",
    deps = [
        ":greeter-lib_project",
    ],
)

js_test(
    name = "greeter-lib_test",
    data = [
        ":greeter-lib_project",
        ":greeter-lib_test_lib",
    ],
    entry_point = "tests/greetingbuilder.test.js",
)

npm_package(
    name = "pkg",
    srcs = [
        ":greeter-lib_project",
        "package.json",
    ],
    package = "greeter-lib",
    visibility = ["//visibility:public"],
)

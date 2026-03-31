load("@aspect_rules_js//js:defs.bzl", "js_binary")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@npm//:defs.bzl", "npm_link_all_packages")

npm_link_all_packages(name = "node_modules")

# Compiles TypeScript to JavaScript.
ts_project(
    name = "greeter_ts",
    srcs = ["src/main.ts"],
    tsconfig = "tsconfig.json",
    transpiler = "tsc",
    deps = [
        "//examples/js/hello-world/greeter-lib",
    ],
)

# Creates an executable Node.js binary.
js_binary(
    name = "greeter",
    entry_point = "src/main.js",
    data = [
        ":greeter_ts",
        ":node_modules/greeter-lib",
    ],
)

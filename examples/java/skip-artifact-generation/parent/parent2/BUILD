java_library(
    name = "parent2",
    srcs = glob(["src/main/java/**/*.java"]),
    # these deps get pulled into the pom generated for *this* package
    # because the reference below has pomgen mode == skip
    deps = ["//examples/java/skip-artifact-generation/passthrough:set1"],
    runtime_deps = ["@maven//:org_antlr_ST4"],
)

java_binary(
    name = "Main",
    srcs = glob(["src/**/*.java"]),
    deps = [":parent2"],
)
    

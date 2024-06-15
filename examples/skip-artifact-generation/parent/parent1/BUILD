java_library(
    name = "parent1",
    srcs = glob(["src/main/java/**/*.java"]),
    # these deps get pulled into the pom generated for *this* package
    # because the reference below has pomgen mode == skip
    deps = ["//examples/skip-artifact-generation/passthrough:set1"],
    runtime_deps = ["@maven//:org_antlr_stringtemplate"],
)

java_binary(
    name = "main",
    main_class = "com.pomgen.example.lib1.Main",
    runtime_deps = [":parent1"],
)
    

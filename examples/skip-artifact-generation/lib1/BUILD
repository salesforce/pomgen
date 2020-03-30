java_library(
    name = "lib1",
    srcs = glob(["src/main/java/**/*.java"]),
    # these deps get pulled into the pom generated for *this* package
    deps = ["//examples/skip-artifact-generation/lib1_transitives:set1"],
)

java_binary(
    name = "Main",
    srcs = glob(["src/**/*.java"]),
    deps = [":lib1"],
)
    

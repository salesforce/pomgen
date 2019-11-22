java_library(
    name = "juicer",
    srcs = glob(["src/main/java/**/*.java"]),
    deps = ["//example/healthyfoods/fruit-api", 
            "//example/healthyfoods/vegetable-api",
            "//example/wintervegetables",
            "@com_google_guava_guava//jar"]
)

java_binary(
    name = "make-juice",
    runtime_deps = [":juicer"],
    main_class = "com.pomgen.example.Main",
)

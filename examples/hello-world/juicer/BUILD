java_library(
    name = "juicer",
    srcs = glob(["src/main/java/**/*.java"]),
    deps = ["//examples/hello-world/healthyfoods/fruit-api", 
            "//examples/hello-world/healthyfoods/vegetable-api",
            "//examples/hello-world/wintervegetables",
            "@maven//:com_google_guava_guava",
    ]
)

java_binary(
    name = "make-juice",
    runtime_deps = [":juicer"],
    main_class = "com.pomgen.example.Main",
)

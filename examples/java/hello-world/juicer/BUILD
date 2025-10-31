java_library(
    name = "juicer_lib",
    srcs = glob(["src/main/java/**/*.java"]),
    deps = ["//examples/java/hello-world/healthyfoods/fruit-api", 
            "//examples/java/hello-world/healthyfoods/vegetable-api",
            "//examples/java/hello-world/wintervegetables:wintervegetables_lib2",
            "@maven//:com_google_guava_guava",
    ]
)

java_binary(
    name = "make-juice",
    runtime_deps = [":juicer_lib"],
    main_class = "com.pomgen.example.Main",
)

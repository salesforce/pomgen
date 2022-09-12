java_library(
    name = "coollib",
    srcs = glob(["src/main/java/**/*.java"]),
    deps = ["//examples/compile-only-dependencies/fancy",
            "@maven//:com_google_guava_guava",
    ]
)

java_binary(
    name = "make-coollib",
    runtime_deps = [":coollib"],
    main_class = "com.pomgen.example.Main",
)

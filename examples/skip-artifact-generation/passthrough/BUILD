java_library(
    name = "set1",
    runtime_deps = [
        "@maven//:com_google_guava_guava",
        ":set2",
    ],
    visibility = ["//visibility:public"],
)

java_library(
    name = "set2",
    runtime_deps = [
        "//examples/skip-artifact-generation/lib",
        "@maven//:com_google_guava_guava",
        ":set3",
    ],
)

java_library(
    name = "set3",
    runtime_deps = [
        "@maven//:org_apache_commons_commons_lang3",
    ],
)

java_library(
    name = "set1",
    runtime_deps = [":set2",],
    exports = ["@poppy_mvn//:com_google_guava_guava",],
    visibility = ["//visibility:public"],
)

java_library(
    name = "set2",
    runtime_deps = [":set3", "//examples/java/skip-artifact-generation/lib",],
)

java_library(
    name = "set3",
    runtime_deps = ["@poppy_mvn//:org_apache_commons_commons_lang3",],
)

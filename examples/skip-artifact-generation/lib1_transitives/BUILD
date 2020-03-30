java_library(
    name = "set1",
    runtime_deps = [
        "@com_google_guava_guava//jar",
        ":set2",
    ],
    visibility = ["//visibility:public"],
)

java_library(
    name = "set2",
    runtime_deps = [
        "//examples/skip-artifact-generation/lib2",
        "@com_google_guava_guava//jar",
        ":set3",
    ],
)

java_library(
    name = "set3",
    runtime_deps = [
        "@org_apache_commons_commons_lang3//jar",
    ],
)

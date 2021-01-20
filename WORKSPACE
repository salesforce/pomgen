workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "4.0"
RULES_JVM_EXTERNAL_SHA = "31701ad93dbfe544d597dbe62c9a1fdd76d81d8a9150c2bf1ecf928ecdf97169"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
    url = "https://github.com/bazelbuild/rules_jvm_external/archive/%s.zip" % RULES_JVM_EXTERNAL_TAG,
)

load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven")


load("@rules_jvm_external//:repositories.bzl", "rules_jvm_external_deps")
rules_jvm_external_deps()
load("@rules_jvm_external//:setup.bzl", "rules_jvm_external_setup")
rules_jvm_external_setup()

maven_install(
    name = "maven",
    artifacts = [
        maven.artifact(group = "com.google.guava", artifact = "guava", version = "23.0", exclusions = ["*:*"]),
        maven.artifact(group = "org.apache.commons", artifact = "commons-lang3", version = "3.9", exclusions = ["*:*"]),
        maven.artifact(group = "org.apache.commons", artifact = "commons-math3", version = "3.6.1", exclusions = ["*:*"]),
        maven.artifact(group = "org.antlr", artifact = "stringtemplate", version = "3.2.1",),
        maven.artifact(group = "org.antlr", artifact = "ST4", version = "4.0.7",exclusions = ["antlr:antlr"]),
    ],
    repositories = [
        "https://repo1.maven.org/maven2",
    ],
    version_conflict_policy = "pinned",
    strict_visibility = True,
    generate_compat_repositories = True,
    maven_install_json = "//:maven_install.json",  # regenerate: bazel run @unpinned_maven//:pin
    resolve_timeout = 1800,
)

load("@maven//:defs.bzl", "pinned_maven_install")
pinned_maven_install()

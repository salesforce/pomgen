workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "5.2"
RULES_JVM_EXTERNAL_SHA = "f86fd42a809e1871ca0aabe89db0d440451219c3ce46c58da240c7dcdc00125f"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
        url = "https://github.com/bazelbuild/rules_jvm_external/releases/download/%s/rules_jvm_external-%s.tar.gz" % (RULES_JVM_EXTERNAL_TAG, RULES_JVM_EXTERNAL_TAG),
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
        maven.artifact(group = "com.google.guava", artifact = "guava", version = "33.4.8-jre", exclusions = ["*:*"]),
        maven.artifact(group = "org.apache.commons", artifact = "commons-lang3", version = "3.18.0", exclusions = ["*:*"]),
        maven.artifact(group = "org.apache.commons", artifact = "commons-math3", version = "3.6.1", exclusions = ["*:*"]),
        maven.artifact(group = "org.antlr", artifact = "ST4", version = "4.0.7",exclusions = ["antlr:antlr"]),
    ],
    repositories = [
        "https://repo1.maven.org/maven2",
    ],
    version_conflict_policy = "pinned",
    strict_visibility = False,
    generate_compat_repositories = False,
    # to regenerate the pinned file: bazel run @unpinned_maven//:pin
    maven_install_json = "//examples/maven_install:maven_install.json",
    resolve_timeout = 1800,
)

load("@maven//:defs.bzl", "pinned_maven_install")
pinned_maven_install()

# this rule is here to test pomgen with multipe maven_install rules
maven_install(
    name = "antlr",
    artifacts = [
        maven.artifact(group = "org.antlr", artifact = "ST4", version = "4.0.7",),
        # org.antlr:ST4:4.0.7 brings in antlr:antr:2.7.7 - we override
        # the version here to 2.7.6 to test how version overrides of transitives
        # carry over into the generate pom files
        maven.artifact(group = "antlr", artifact = "antlr", version = "2.7.6",),
    ],
    repositories = [
        "https://repo1.maven.org/maven2",
    ],
    version_conflict_policy = "pinned",
    strict_visibility = True,
    generate_compat_repositories = False,
    # to regenerate the pinned file: bazel run @unpinned_antlr//:pin
    maven_install_json = "//examples/maven_install:antlr_install.json",
    resolve_timeout = 1800,
)

load("@antlr//:defs.bzl", antlr_pinned = "pinned_maven_install")
antlr_pinned()

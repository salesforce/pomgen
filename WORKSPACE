workspace(name = "pomgen")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

RULES_JVM_EXTERNAL_TAG = "3.3"
RULES_JVM_EXTERNAL_SHA = "d85951a92c0908c80bd8551002d66cb23c3434409c814179c0ff026b53544dab"

http_archive(
    name = "rules_jvm_external",
    strip_prefix = "rules_jvm_external-%s" % RULES_JVM_EXTERNAL_TAG,
    sha256 = RULES_JVM_EXTERNAL_SHA,
    url = "https://github.com/bazelbuild/rules_jvm_external/archive/%s.zip" % RULES_JVM_EXTERNAL_TAG,
)

load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven")

maven_install(
    name = 'maven',
    artifacts = [
        maven.artifact(group = 'com.google.guava', artifact = 'guava', version = '23.0', exclusions = ['*:*']),
        maven.artifact(group = 'org.apache.commons', artifact = 'commons-lang3', version = '3.9', exclusions = ['*:*']),
        maven.artifact(group = 'org.apache.commons', artifact = 'commons-math3', version = '3.6.1', exclusions = ['*:*']),
    ],
    repositories = [
        'https://repo1.maven.org/maven2',
    ],
    version_conflict_policy = 'pinned',
    strict_visibility = True,
    generate_compat_repositories = True,
    maven_install_json = '//:maven_install.json',  # regenerate: bazel run @unpinned_maven//:pin
    resolve_timeout = 1800,
)

load("@maven//:defs.bzl", "pinned_maven_install")
pinned_maven_install()

load("@maven//:compat.bzl", "compat_repositories")
compat_repositories()
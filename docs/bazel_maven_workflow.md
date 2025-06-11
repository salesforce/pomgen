# Working across Bazel and Maven

Some users may need to work across Bazel and Maven projects. There are two common use cases:


## Use jars produced by Maven in a Bazel project

1. Copy or link the jar to same directory the BUILD file lives in (or a subdirectory)
1. Create a `java_import` rule that points to the jar
1. Replace the `maven_install` based dependency (starting with `@`) with the `java_import` target (starting with `//`)
1. Build as usual


### Example

Copy the jar.
```
cd $BUILD_DIR
cp ~/.m2/repository/org/slf4j/slf4j-api/1.7.29/slf4j-api-1.7.30-SNAPSHOT.jar .
```
Or symlink to it. The advantage of using a link is that the jar can be updated by Maven without having to re-copy it.
```
cd $BUILD_DIR
ln -s ~/.m2/repository/org/slf4j/slf4j-api/1.7.29/slf4j-api-1.7.30-SNAPSHOT.jar .
```
Create `java_import` rule in the BUILD file. In this example, we'll use slf4j-api. This assumes that the jar the  has been copied or symlinked to the same directory as the BUILD file.
```
java_import(
    name = "org_slf4j_slf4j_api",
    jars = [":slf4j-api-1.7.30-SNAPSHOT.jar"],
)
```
Then, in the deps attribute(s) replace the `maven_install` rule for slf4j-api with the `java_import` rule that was just created.
```
java_library(
    name = "fruit-api",
    srcs = glob(["src/main/java/**/*.java"]),
    visibility = ["//visibility:public"],
    deps = [
      ...
      ":org_slf4j_slf4j_api", # instead of "@maven//:org_slf4j_slf4j_api"
      ...
    ],
)
```


## Build jars with Bazel and use them in a Maven project

Similar to above, we can build jars using Bazel, so that they can be used in Maven projects:

1. Make code changes to the library which you want to release a jar for.
1. Build the library by running `bazel build path/to/library/...`.
1. Run `bazel run @poppy//package/maven -- -a pomgen,install -l path/to/library` to generate poms and install the jars to `~/.m2/repository`.
1. Update the pom.xml in the consuming Maven project to use the right jar version

See [this example](../examples/hello-world#installing-maven-artifacts-into-the-local-maven-repository) for more information.

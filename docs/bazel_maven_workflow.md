# Working across Bazel and Maven

Some users may need to work across Bazel and Maven projects. Particularly there are two common use cases.

## Use SNAPSHOT jars produced by Maven in a Bazel project

To use SNAPSHOT jars in a Bazel project just like one would in Maven, the following steps need to be taken.

### The process for using SNAPSHOT jars produced by Maven

1. Copy or link SNAPSHOT jar to same directory as or relative to Bazel BUILD file.
2. Create a java_import rule that points to the SNAPSHOT jar.
3. Replace maven_install rule in dependency list with java_import.
4. Build and profit.

#### Example
Copy the SNAPSHOT jar.
```
cd $BUILD_DIR
cp ~/.m2/repository/org/slf4j/slf4j-api/1.7.29/slf4j-api-1.7.30-SNAPSHOT.jar .
```
Or symlink to it. The advantage of using a link is that the jar can be updated by Maven and re-run build in Bazel.
```
cd $BUILD_DIR
ln -s ~/.m2/repository/org/slf4j/slf4j-api/1.7.29/slf4j-api-1.7.30-SNAPSHOT.jar .
```
Create java_import rule in BUILD file. In this example, we'll use slf4j-api. This assumes that the location of the SNAPSHOT has been copied or symlinked to the same directory as the BUILD file.
```
java_import(
    name = "org_slf4j_slf4j_api",
    jars = [":slf4j-api-1.7.30-SNAPSHOT.jar"],
)
```
Then, in the deps attribute replace maven_install rule for slf4j-api with the java_import that was just created.
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

## Build SNAPSHOT jars with Bazel and use them in a Maven project
Similar to above, we can generate SNAPSHOT jars using Bazel, so that they can be used in Maven projects. See below for detailed steps.

#### The process for generating SNAPSHOT jars using Bazel
1. Make code changes to the library which you want to release SNAPSHOT jar for.
1. Build your library by running `bazel build path/to/library` (the default bazel target MUST be the one building the library jar)
1. Run `bazel run @pomgen//maven -- -a pomgen -t path/to/library` to generate poms
1. Run `bazel run @pomgen//maven -- -a install -t path/to/library` to install the library into `~/.m2/repository`.
1. Update the pom.xml in the consuming Maven project to use <new version>-SNAPSHOT of your library.
 
#### Example
Make some code changes in `examples/hello-world/healthyfoods/fruit-api`.

Run bazel build.
```
bazel build //examples/hello-world/healthyfoods/fruit-api
```
Update artifact version.
```
bazel run @pomgen//:update -- --package examples/hello-world/healthyfoods/fruit-api
```
Generate pom(s).
```
bazel run @pomgen//maven -- -a pomgen
```
Install the built library into `~/.m2/repository`.
```
bazel run @pomgen//maven -- -a install
```
Then, update the pom.xml of the consuming Maven project.
```
<dependency>
    <groupId>com.pomgen.example</groupId>
    <artifactId>fruit-api</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>
```
Now you can compile your Maven project, it should be using the latest SNAPSHOT jars produced by Bazel.

# java_import

Limited support for `java_import` usage exists, limited because of poppy's assumption that there's a 1-1 mapping between Bazel Package and produced jar artifact.

In practice, this means that the `java_import` rule can only reference a single jar file ([example](oldfruit/BUILD)). The corresponding [BUILD.pom](oldfruit/MVN-INF/BUILD.pom) file must specify the `jar_path` attribute.


### Generating poms

From the root of the repository:

```
bazel build examples/java/java-import/...
```

```
bazel run @poppy//package/maven -- -a pomgen,install -l examples/java/java-import
```

The cmd above installs jars and poms into `~/.m2/repository`. The `java_import` jar is at:
```
~/.m2/repository/com/pomgen/example/java/oldfruit/1.0.0-SNAPSHOT/oldfruit-1.0.0-SNAPSHOT.jar
```

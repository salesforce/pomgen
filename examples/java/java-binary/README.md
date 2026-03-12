# Custom target with java-binary

This example demonstrates how to use `poppy` with a `java_binary` target, specifically with the special implicit `_deploy.jar` target, that produces a self-contained jar.


## Structure

- `BUILD`: Defines a `java_binary` target
- `MVN-INF/BUILD.pom`: Artifact metadata with `target_name = "java-binary_deploy.jar"` to reference the `_deploy.jar`. This is necessary to make sure poppy is aware of this non-default target
- `MVN-INF/LIBRARY.root`: Marks this as a library root
- `src/main/java/com/pomgen/example/Main.java`: Simple main class

## Commands

Generate pom, build the jar, and install to local Maven repository:

```bash
bazel run @poppy//package/maven -- -a pomgen,build,install -l examples/java/java-binary
```

Verify:

```bash
java -jar $HOME/.m2/repository/com/pomgen/example/java-binary/1.0.0-SNAPSHOT/java-binary-1.0.0-SNAPSHOT.jar
```

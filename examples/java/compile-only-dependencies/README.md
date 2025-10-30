# Compilation time only dependencies

There are some dependencies that are needed only at compilation time, for example Lombok. To ensure compile-time only dependencies are not included at runtime, Bazel has the `neverlink` attribute, which can be added to `java_library` rules. `poppy` honors the `neverlink` attribute and will not add jars produced by neverlinked `java_library` target to generated poms.


### Try this example

From the root of the repository:

```
bazel build examples/java/compile-only-dependencies/...
```

```
bazel run @poppy//package/maven -- -a pomgen,install -l examples/java/compile-only-dependencies
```

It should pass although `examples/compile-only-dependencies/fancy` has no `BUILD.pom` file. The generated pom does not include the `neverlink` dependency.

# Compilation time only dependencies

Some dependencies are needed only at compilation time, for example Lombok. To ensure compile-time only dependencies are not included at runtime, Bazel has the `neverlink` attribute, which can be added to `java_library` rules. `poppy` honors the `neverlink` attribute and will not add jars produced by neverlinked `java_library` target to generated poms.


### Try this example

From the root of the repository:

```
bazel run @poppy//package/maven -- -a pomgen -l examples/java/compile-only-dependencies/coollib
```

The generated pom for `coollib` does not include `fancy` as a dependency, because fancy has `neverlink = 1` set.

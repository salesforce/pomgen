# Compilation time only dependencies should not be evaluated by pomgen

There are some dependencies that are needed only at compilation time, for example Lombok. To ensure compile-time only dependencies are not included at runtime, Bazel has the `neverlink` attribute, which can be added to `java_library` rules.
Typically compile-time only dependencies won't have a `BUILD.pom` file, so they have to be ignored by `pomgen`.

### Try this example

From the root of the repository:

```
bazel build examples/compile-only-dependencies/...
```

```
bazel run @pomgen//maven -- -a pomgen,install -t examples/compile-only-dependencies
```

It should pass although `examples/compile-only-dependencies/fancy` has no `BUILD.pom` file. The generated pom does not include the `neverlink` dependency.
# Compilation time only deps should not be evaluated by pomgen

There are some dependencies that are needed only at compilation time, like for example Lombok.
This kind of dependencies can be managed differently by Bazel adding the attribute `neverlink = 1` to `java_library`.
Most likely those dependencies won't have a `BUILD.pom` file, so they have to be ignored by `pomgen`.

### Try this example

From the root of the repository:

```
bazel build examples/dependency-management/...
```

```
bazel run @pomgen//maven -- -a pomgen,install -t examples/compile-only-dependencies
```

It should pass even if `examples/compile-only-dependencies/fancy` has no `BUILD.pom` file.
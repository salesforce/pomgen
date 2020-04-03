# Skip Mode

## Looking around

This example shows how `pom_generation_mode = "skip"` can be used. [This pom generation mode](lib1_transitives/MVN-INF/BUILD.pom) can be used to mark bazel targets that [provide dependencies only](lib1_transitives/BUILD), but that do not produce any Maven artifacts. All dependencies of these types of targets will be added to pom generated for the referencing target.

The libraries in this example reference each other the following way:

```
lib1 -> lib1_transitives -> lib2
```

### Generating poms

From the root of the repository:

```
bazel run @pomgen//:pomgen -- --package examples/skip-artifact-generation --destdir /tmp/pomgen --recursive
```

The command above generates 2 poms, one for [lib1](lib1/BUILD) and one for [lib2](lib2). All dependencies from [lib1_transitives](lib1_transitives/BUILD) are included in lib1's pom.



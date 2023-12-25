# Skip Mode


## Looking around

The [skip pom generation mode](passthrough/MVN-INF/BUILD.pom) can be used to mark bazel targets that [provide dependencies only](passthrough/BUILD), but that do not produce any Maven artifacts. All dependencies of these types of targets will be added to pom generated for the referencing target.

The libraries in this example reference each other the following way:

```
parent (contains 2 artifacts: parent1 and parent2) -> passthrough -> lib
```


### Generating poms

From the root of the repository:

```
bazel run @pomgen//:pomgen -- --package examples/skip-artifact-generation/parent --destdir /tmp/pomgen
```

The command above generates 3 poms, for:
  - [parent/parent1](parent/parent1/BUILD)
  - [parent/parent2](parent/parent2/BUILD)
  - [lib](lib/BUILD)

All dependencies specified in the  [passthrough package](passthrough/BUILD) are included in the pom's of `parent1` and `parent2`.



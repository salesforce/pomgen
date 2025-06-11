# Overridding dependencies

rules-jvm-external provides an [override mechanism](https://github.com/bazelbuild/rules_jvm_external?tab=readme-ov-file#overriding-generated-targets) that allows to switch out a group and artifact id with another dependency label. This features allows overriding dependencies that are brought in transitively (ie these dependencies are dragged in through top level dependencies referenced in bazel build files). pomgen honors the same override mechanism.


## Example

The [library in this example](BUILD) depends on `org.antlr:ST4` (`@antlr//:org_antlr_ST4`). This jar in turn drags in 3 transitives (the transitive closure is):
- `org.antlr:antlr-runtime` references
- `org.antlr:stringtemplate` references
- `antlr:antlr`


## Generate pom

Generate a pom.xml file for this example's library:

```
bazel run @pomgen//:pomgen -- --package examples/dep-overrides --destdir /tmp/overrides
```

Have a look at the generated pom.xml - note that the pom brings in the transitives listed above.


## Override a transitive

On order to override dependencies brought in transitively, pomgen needs to be pointed to one or more "overrides" file(s). Add to the `[general]` section of the [root .pomgenrc](../../.pomgenrc):

```
override_file_paths=examples/dep-overrides/overrides.bzl
```

The content of the [overrides file](overrides.bzl) is:
```
"org.antlr:stringtemplate": "@maven//:com_google_guava_guava"
```
(although this example only has a single override, many override rules are allowed)

This means that the `stringtemplate` dependency will be overridden with `guava`.  Note that Guave happens to be defined in a different maven install rule (`@maven` instead of `@antlr`): overrides may cross maven install boundaries.

Regenerate the pom:

```
bazel run @poppy//:gen -- --package examples/dep-overrides --destdir /tmp/overrides
```

Have a look at the generated pom.xml - since the `stringtemplate` dependency is replaced by `guava`, the `antlr` dependency, previously dragged in by `stringtemplate`, is no longer there.


# Change Detection

pomgen tracks whether an artifact has changed since it was last released. It also tracks the last released version of each artifact. It uses this information to decide whether an artifact needs to be released and to determine which artifact version to use in `<dependency>` references in generated poms.

Change detection is most useful for libraries that have a large number of transitives, because it prevents the (unchanged) transitives from being released over and over again when the main library changes.

## Example

```
A1 -> A2 -> A3
```

A1 references A2, A2 references A3. These are all source artifacts in the same repository, and their BUILD files look similar to this:

A1's BUILD file

```
java_library(
    name = "a1",
    deps = ["projects/libs/a2"],
    ...
```

A2's BUILD file

```
java_library(
    name = "a2",
    deps = ["projects/libs/a3"],
    ...
```

When pomgen runs for A1, it will use change detection to determine whether A2 and A3 actually need to be released:
 - If A2 and A3 have not changed since they were last released, then the pom.xml file generated for A1 will contain references to the previously released version of A2.
 - If A2 has changed since it was last released, but A3 has not, then pomgen will generate a new pom.xml for both A1 and A2. A2's reference to A3 will use the last released version.
 - If A3 has changed but not A2, then pomgen generates a new pom.xml for A3, and also a new pom.xml for A2, which has the updated reference (version) to A3.

## Release Snapshoting

pomgen uses a hash based on the git repository state to track the state of an artifact. Updating this hash requires running the pomgen `update` command. This has to happen as part of the artifact release process.

In order to update the artifact's hash and the released artifact's version, use the following command:

```
bazel run @pomgen//:update -- --package <path/to/bazel/package> \ 
    --update_released_artifact_hash_to_current \
    --new_released_version <released version>
```

For example, the following command updates the release state of all artifacts under the hello-world directory.

```
bazel run @pomgen//:update -- --package examples/hello-world \
    --update_released_artifact_hash_to_current \
    --new_released_version 1.0.0
```

## Disabling Change Detection

Change detection is enabled by default. It can be disabled:
- On a per-artifact basis by setting the `change_detection` attribute of the `maven_install` rule in the `BUILD.pom` file to `False`
- By setting the `--force` argument when running `pomgen`
- By setting the `-f` argument when running `//maven`

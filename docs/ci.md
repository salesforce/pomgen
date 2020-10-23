# CI Setup

Releasing Libraries to a Maven Repository, such as Nexus, is typically done from a CI job.

At a high level, pomgen is meant to be called the following way from a CI job.

Note that pomgen [assumes you are using git](https://github.com/salesforce/pomgen/issues/30).

### Build the binary artifacts

```
bazel build <bazel package>
```

### Update Artifact versions for releasing

Typically, versions defined in BUILD.pom files end with `-SNAPSHOT` during development. Before releasing to the Maven Repository, the -SNAPSHOT suffix needs to be removed. This is done using the `update` target:

```
bazel run @pomgen//:update -- --package <bazel package> --new_version <release version>
```

pomgen query can be used to get the value to use as release version:

```
bazel run @pomgen//:query -- --package <bazel package> --library_release_plan_json
```

Look for the attribute called `proposed_release_version`.

See this [related issue](https://github.com/salesforce/pomgen/issues/29) to make this easier.

### Generate poms

```
bazel run @pomgen//maven -- -a pomgen -t <bazel package>
```

### Upload Artifacts to the Maven Repository

```
bazel run @pomgen//maven -- -a deploy_all
```

"deploy_all" includes sources and javadoc.

### Update release metadata

#### Generate pom goldfiles

These files are used by pomgen to determine whether a new release is required because the pom has changed since the last release.

```
bazel run @pomgen//:pomgen -- --package <bazel package> --destdir <root of repo> --recursive --pom_goldfile
```

#### Write BUILD.pom.released files

These files are used by pomgen to determine whether any binary Artifact has changed since it was last released.

```
bazel run @pomgen//:update -- --package <bazel package> --new_released_version <release version> --update_released_artifact_hash_to_current
```

### Update Artifact versions for development

Increment the Artifact versions based on the specified increment strategy, and re-add the "-SNAPSHOT" version qualifier:

```
bazel run @pomgen//:update -- --package <bazel package> --update_version_using_version_increment_strategy

bazel run @pomgen//:update -- --package <bazel package> --add_version_qualifier SNAPSHOT
```

### Commit metadata changes back to the repository


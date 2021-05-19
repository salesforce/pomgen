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
bazel run @pomgen//:pomgen -- --package <bazel package> --destdir <root of repo> --pom_goldfile
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

Commit and send PR.


## About propsed versions

`pomgen query` can be used to determine release and development versions to use. This information is part of the json response when asking for `--library_release_plan_json`.

For example:

```
bazel run @//:query -- --package examples/hello-world/juicer --library_release_plan_json
```

The cmd above asks for release information about the *juicer* library. Because that library references the *healthyfoods* and *wintervegetables* libraries, information for those 2 libraries is returned also.

The relevant versioning information in the returned payload is:

```
[
  {
    "library_path": "examples/hello-world/juicer",
    "proposed_release_version": "3.0.0",
    "proposed_next_dev_version": "3.1.0-SNAPSHOT"
  },
  {
    "library_path": "examples/hello-world/healthyfoods",
    "proposed_release_version": "1.0.0",
    "proposed_next_dev_version": "1.1.0-SNAPSHOT"
  },
  {
    "library_path": "examples/hello-world/wintervegetables",
    "proposed_release_version": "2.0.0",
    "proposed_next_dev_version": "2.1.0-SNAPSHOT"
  }
]
```

The "proposed" versions above are based on the [version increment strategies](mdfiles.md#maven_artifact_updateversion_increment_strategy) specified by each library.

In this example, pomgen does not distinguish between the main library being queried, *juicer*, and the 2 transitive libraries.

### Using a different version increment mode for transitives

If library owners want to tightly control when their [semver](https://semver.org) version components are incremented, then transitive library releases cannot change their semver version, since library owners have no control over transitive releases. pomgen supports another transitives versioning scheme for this use case - it can be enabled by setting `transitives_versioning_mode=counter` in the [pomgenrc file](../README.md#configuration). This versioning mode works as follows:

1. IMPORTANT this versioning scheme only affects libraries released **transitively**. So in the example above, this versioning logic would be used for *healthyfoods* and *wintervegetables* only, NOT for *juicer*
1. Start with the last released version, for example 1.2.3. If the library has never been released, the last released version defaults to 0.0.0
1. If the last released version is not followed by the qualifier "-rel-", add it, for example 1.2.3-rel-
1. Increment the number following the "-rel-" qualifier.  If there is no number, start with 1. For example 1.2.3-rel-1.
1. The next development version does not change.

Example with this versioning mode enabled:

```
bazel run @//:query -- --package examples/hello-world/juicer --library_release_plan_json
```

```
[
  {
    "library_path": "examples/hello-world/juicer",
    "proposed_release_version": "3.0.0",
    "proposed_next_dev_version": "3.1.0-SNAPSHOT"
  },
  {
    "library_path": "examples/hello-world/healthyfoods",
    "proposed_release_version": "0.0.0-rel-1",
    "proposed_next_dev_version": "1.0.0-SNAPSHOT"
  },
  {
    "library_path": "examples/hello-world/wintervegetables",
    "proposed_release_version": "0.0.0-rel-1",
    "proposed_next_dev_version": "2.0.0-SNAPSHOT"
  }
]
```

# pomgen Example

## Looking around

This example has 3 libraries. A library is a collection of one or more Bazel Packages that produce Maven Artifacts. A library is defined by the presence of a [LIBRARY.root](healthyfoods/MVN-INF/LIBRARY.root) marker file.

A Bazel Package that produces a Maven Artifact must have a [BUILD.pom](healthyfoods/fruit-api/MVN-INF/BUILD.pom) file that defines Maven specific metadata.

The libraries in this example are, and reference each other in this order:
- [juicer](juicer)
- [wintervegetables](wintervegetables)
- [healthyfoods](healthyfoods)

### Before running pomgen

Make sure you have installed the required [external dependencies](../README.md#external-dependencies).

From the root of the repository:

```
bazel build //...
```

Make sure the pomgen tests pass.  From the root of the repository:

```
bazel test //...
```

### pomgen query

The [query_maven_metadata](../query_maven_metadata.py) script provides information about Libraries and Maven Artifacts in the repository.  It also shows information on whether a Library needs to be released or not.

From the root of the repository:

```
bazel run @pomgen//:query -- --package example/juicer --library_release_plan_tree
```

The output looks similar to this:
```
example/juicer ++ 3.0.0-SNAPSHOT
  example/wintervegetables ++ 2.0.0-SNAPSHOT
    example/healthyfoods ++ 1.0.0-SNAPSHOT
  example/healthyfoods ++ 1.0.0-SNAPSHOT

++ artifact has never been released
```

The output shows:
- juicer references wintervegetables, which references healthyfoods
  - juicer also references healthyfoods directly
- The version of each library
- Whether the library needs to be released or not
  - In this case they all need to be released because pomgen is not aware of any previous release

### Generating poms

From the root of the repository:

```
bazel run @pomgen//:pomgen -- --package example/juicer --destdir /tmp/pomgen --recursive
```

The command above generates 4 poms, one for each Maven Artifact (healthyfoods has 2 Maven Artifacts)

### Updating Maven Metadata

There's also [a script](../update_maven_metadata.py) that can be used to update Maven metadata. For example, from the root of the repository:

```
bazel run @pomgen//:update -- --package example/healthyfoods --new_version 5.0.0-SNAPSHOT

```

The command above updates the version of all artifacts under `example/healthyfoods` to 5.0.0-SNAPSHOT.

## Processing generated pom.xml files

pomgen generates pom.xml files, based on whether a library needs to be released or not. The final step is to run the Maven command line for each generated pom, and to do something with it. There is a [wrapper script](../maven/maven.sh) that does this. Before running, make sure you have the required [external dependencies](../maven/README.md#external-dependencies).

### Installing Maven Artifacts into the local Maven Repository

This is useful for running Maven builds locally that consume Bazel produced Artifacts.

From the root of the repository:

```
bazel run @pomgen//maven -- -a pomgen,install -t example
```

The command above will first call pomgen to generate poms and then invoke Maven to install the Artifacts (poms and jars) into the local Maven Repository.

The maven.sh wrapper scripts is driven by the presence of pom.xml files. It is possible that pom.xml files are left around from previous invocations, running `clean` removes these poms and some other artifacts that are created as a side effects of running Maven.

```
bazel run @pomgen//maven -- -a clean
```


## Uploading Artifacts to a Remote Maven Artifact Repository

Use the `deploy` action instead of the `install` action:

```
bazel run @pomgen//maven -- -a pomgen,deploy -t example
```

Running deploy requires the environment variable `REPOSITORY_URL` to be set. REPOSITORY_URL has only been tested with Nexus endpoints. The format is

```
https://hostname/nexus/service/local/repositories
```

The maven script appends `$repository/content` to the value of REPOSITORY_URL.

`$repository` will be replaced with `snapshots` if the version of the artifact being processed ends with -SNAPSHOT, otherwise `$repository` is replaced with `releases`.

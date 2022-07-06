# Hello World for pomgen 

## Looking around

This example has 3 libraries. A library is a collection of one or more Bazel Packages that produce Maven Artifacts. A library is defined by the presence of a [LIBRARY.root](healthyfoods/MVN-INF/LIBRARY.root) marker file. In the Maven World, a Library would be a Maven project with one or more modules.

A Bazel Package that produces a Maven Artifact must have a [BUILD.pom](healthyfoods/fruit-api/MVN-INF/BUILD.pom) file that defines Maven specific metadata. Note that the `java_library` target that builds the jar Maven Artifact must be the default target, ie it must have the same name as the directory its BUILD file lives in.

The libraries in this example are, and reference each other in this order:
- [juicer](juicer)
- [wintervegetables](wintervegetables)
- [healthyfoods](healthyfoods)

### Before running pomgen

Make sure you have installed the required [external dependencies](../../README.md#external-dependencies).

From the root of the repository:

```
bazel build //...
```

Make sure the pomgen tests pass.  From the root of the repository:

```
bazel test //...
```

### pomgen query

The [metadata query](../../query.py) script provides information about Libraries and Maven Artifacts in the repository.  It also shows information on whether a Library needs to be released or not.

From the root of the repository:

```
bazel run @pomgen//:query -- --package examples/hello-world/juicer --library_release_plan_tree
```

The output looks similar to this:
```
examples/hello-world/juicer ++ 3.0.0-SNAPSHOT
  examples/hello-world/healthyfoods ++ 1.0.0-SNAPSHOT
  examples/hello-world/wintervegetables ++ 2.0.0-SNAPSHOT
    examples/hello-world/healthyfoods ++ 1.0.0-SNAPSHOT
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
bazel run @pomgen//:pomgen -- --package examples/hello-world/juicer --destdir /tmp/pomgen
```

The command above generates 5 poms, one for each Maven Artifact (healthyfoods has 3 Maven Artifacts)

### Updating Maven Metadata

There's also [a script](../../update.py) that can be used to update Maven metadata. For example, from the root of the repository:

```
bazel run @pomgen//:update -- --package examples/hello-world/healthyfoods --new_version 5.0.0-SNAPSHOT

```

The command above updates the version of all artifacts under `example/healthyfoods` to 5.0.0-SNAPSHOT.

## Processing generated pom.xml files

pomgen generates pom.xml files, based on whether a library needs to be released or not. The final step is to run the Maven command line for each generated pom, and to do something with it. There is a [wrapper script](../../maven/maven.sh) that does this. Before running, make sure you have the required [external dependencies](../../maven/README.md#external-dependencies).

### Installing Maven Artifacts into the local Maven Repository

This is useful for running Maven builds locally that consume Bazel produced Artifacts.

From the root of the repository:

```
bazel run @pomgen//maven -- -a pomgen,install -t examples/hello-world
```

The command above will first call pomgen to generate poms and then invoke Maven to install the Artifacts (poms and jars) into the local Maven Repository.

The maven.sh wrapper scripts is driven by the presence of pom.xml files. It is possible that pom.xml files are left around from previous invocations, running `clean` removes these poms and some other artifacts that are created as a side effects of running Maven.

```
bazel run @pomgen//maven -- -a clean
```


## Uploading Artifacts to a Remote Maven Artifact Repository

Use the `deploy` action instead of the `install` action:

```
bazel run @pomgen//maven -- -a pomgen,deploy -t examples/hello-world
```

Running deploy requires the environment variable `REPOSITORY_URL` to be set. REPOSITORY_URL has only been tested with Nexus endpoints. The format is

```
https://hostname/nexus/service/local/repositories
```

The maven script appends `$repository/content` to the value of REPOSITORY_URL.

`$repository` will be replaced with `snapshots` if the version of the artifact being processed ends with -SNAPSHOT, otherwise `$repository` is replaced with `releases`.

## Advanced use-cases

### Templates for pom-only artifacts

pomgen supports custom pom templates for the purpose of generating pom-only artifacts (`<packaging>pom</packaging>`). This is typically needed when migrating a Maven project to Bazel that has a parent pom, meant to be inherited from: the parent pom still needs to be generated because existing Maven projects may depend on it. 

See this [example pom template](healthyfoods/parentpom/MVN-INF/pom.template) - note that the corresponding [BUILD.pom](healthyfoods/parentpom/MVN-INF/BUILD.pom) file must specify that the `pom_generation_mode` is `template`. The pom file is generated in the same way as described above, when pomgen runs for the library:

```
bazel run @pomgen//:pomgen -- --package examples/hello-world/healthyfoods --destdir /tmp/pomgen
```

#### Template Features

##### Referencing values from the BUILD.pom file

artifact_id, group_id and version from the BUILD.pom file can be referenced in the pom template using the syntax 

```
#{group_id}
#{articat_id}
#{version}
```

See the [example pom template](healthyfoods/parentpom/MVN-INF/pom.template).

##### Referencing versions

The version of known artifacts, both external (maven_jar) and internal (BUILD.pom) can be referenced in the pom template using the following syntax:
```
#{group_id:artifact_id:version}
```
See the [example pom template](healthyfoods/parentpom/MVN-INF/pom.template).

# Java Setup

 - Add a `java_library` rule that builds the jar, make it the [default target](https://bazel.build/concepts/labels) (or [configure](mdfiles.md#maven_artifacttarget_name) the target name)
 - Add a [MVN-INF/BUILD.pom](../examples/java/hello-world/healthyfoods/fruit-api/MVN-INF/BUILD.pom) file to define Maven specific metadata (artifactId etc)
 - Add a [MVN-INF/LIBRARY.root](examples/java/hello-world/healthyfoods/MVN-INF/LIBRARY.root) file to mark the Bazel Package as a library with a single jar artifact

See [this doc](mdfiles.md) for more information on pomgen metadata files.

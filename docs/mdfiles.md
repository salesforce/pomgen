# Metadata Files

pomgen metadata files live at `<bazel-package>/MVN-INF`.


### BUILD.pom (required)

The BUILD.pom files defines how a pom.xml (for this bazel package) should be generated.

Example:

```
maven_artifact(
    group_id = "com.pomgen.example",
    artifact_id = "juicer",
    version = "3.0.0-SNAPSHOT",
    pom_generation_mode = "dynamic",
)

maven_artifact_update(
    version_increment_strategy = "minor",
)
```

#### Required Attributes

##### maven_artifact.group_id

The `<groupId>` for the generated pom.xml.

##### maven_artifact.artifact_id

The `<artifactId>` for the generated pom.xml.

##### maven_artifact.version

The `<version>` for the generated pom.xml.

##### maven_artifact.pom_generation_mode

- dynamic:  The pom is generated based on the `BUILD` file dependencies [example](../examples/hello-world/juicer/MVN-INF/BUILD.pom)
- template: The pom uses a custom template [example](../examples/hello-world/healthyfoods/parentpom/MVN-INF/pom.template)
- skip: No pom is generated for this bazel package [example](../examples/skip-artifact-generation/README.md)

##### maven_artifact_update.version_increment_strategy

Controls how the version attribute is incremented, possible values are `major|minor|patch` [see CI setup](ci.md).

#### Optional Attributes

##### maven_artifact.change_detection

Controls whether change detection should be enabled for this artifact. If set to `False`, this artifact will always be marked as needing to be released (and a new pom will always be generated).

Default value: `True`

##### maven_artifact.generate_dependency_management_pom

If set to `True`, a dependency management only pom is generated in addition to the usual pom [example](../examples/dependency-management).

Default value: `False`

##### maven_artifact.include_deps

Whether pomgen should include dependencies in the generated pom. Setting this to False disables crawling source dependencies referenced by this bazel package. This is useful for some edge cases when uploading self-contained ("uber") jars.

Default value: `True`

##### maven_artifact.additional_change_detected_packages

List of additional bazel packages pomgen should check for changes when
determining whether this artifact needs to be released.

Default value: `[]` (empty list). By default pomgen only checks the package this BUILD.pom file lives in for changes to determine whether this artifact needs to be released.

##### maven_artifact.jar_path

If the jar artifact is not built by bazel (this is unusual), this attribute can be used to point to an alternative jar to use. The path is relative to the location of the `BUILD.pom` file.

Default value: `None`

See the `java_import` [example](../examples/java_import).

### LIBRARY.root (required)

The LIBRARY.root file is a marker file that is currently empty.  It groups together multiple artifacts, defined by BUILD.pom files, into a single "library". All artifacts that belong to a single library are processed (installed/uploaded) together. Change detection also operates at the library level. If a single artifact in a library has changed, then all artifacts in the library are marked as needing to be released.

Whether an artifact belongs to a library is determined by directory structure: an artifact belongs to the LIBRARY.root found by walking up the file system from the artifact's BUILD.pom file.  For a multi-artifact library, the LIBRARY.root file lives in a parent directory, and multiple BUILD.pom files are defined below it, in subdirectories [example](../examples/hello-world/healthyfoods/MVN-INF/LIBRARY.root). If the library only consists of a single artifact, then the LIBRARY.root file should live next to the artifact's BUILD.pom file [example](../examples/hello-world/juicer/MVN-INF/LIBRARY.root).

:warning: LIBRARY.ROOT files cannot not be nested, ie libraries cannot be defined within other libraries.


### BUILD.pom.released (not user editable)

This file is used by pomgen to track whether an artifact has changed since it was last released [see CI setup](ci.md).


### pom.xml.released (not user editable)

This file is used by pomgen to track whether an artifact has changed since it was last released [see CI setup](ci.md).

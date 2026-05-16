# Configuration

Some `poppy` behavior is driven by an optional configuration file `.poppyrc`. `poppy` looks for this file at the root of the repository it is running in.

Running `poppy` with `--verbose` causes the current config to be echoed.

The file format is:

```
[general]
# Path to the pom template, used when generating pom.xml files for jar artifacts
# Required: True
# Default value: ""
pom_template_path=

# The base filename (without extension) of the generated pom files.
# Default value: pom
pom_base_filename=

# The list of all maven install json files with pinned dependencies, comma-separated. 
# All dependencies that pomgen encounters in BUILD files must exist in one of the files
# listed here.
# Default value: ""
# Example value: tools/maven_install/*.json,another/path/to/mvn_install.json,
maven_install_paths=

# The list of all overridden deps bzl files, comma-separated.
# Default value: empty (not set)
override_file_paths=

[crawler]
# A list of paths, or path prefixes, that are not crawled.
# Any source dependency (a dependency prefixed with //) that starts with one of
# the specified paths is skipped and not processed (and not included in the
# generated pom.xml).
# These dependencies are similar to Maven's "provided" scope: if they are
# needed at runtime, it is expected that the final runtime assembly
# contains them.
# Note that this setting may also be specified in the artifact metadata file,
# this can be useful if the "skipping" should only apply to specific source
# dependencies for that single artifact only.
# Default value: []
# Example value: projects/protos/,
excluded_dependency_paths=

# A list of labels that are skipped over by pomgen.  Any dependency
# that matches one of the specified strings is skipped and not processed
# (and not included in the generated pom.xml).
# These dependencies are similar to Maven's "provided" scope: if they are
# needed at runtime, it is expected that the final runtime assembly
# contains them.
# Default value: []
# Example value: @maven//:com_google_guava_guava,
excluded_dependency_labels=


[artifact]
# Global toggle for change detection (docs/change_detection.md)
# Default value: True
change_detection_enabled=

# Paths not considered when determining whether an artifact has changed
# Default value: src/test,
excluded_relative_paths=

# File names not considered when determining whether an artifact has changed
# Default value: .gitignore,
excluded_filenames=

# Ignored file extensions when determining whether an artifact has changed
# Default value: .md,
excluded_extensions=

# Specifies how to increment the versions of libraries released transitively
# Default value: semver
# Possible values: semver|counter
transitives_versioning_mode=

# Path prefixes for libraries that must always use semver versioning
# Default value: []
always_semver_path_prefixes=

# The classifier used for all jars artifacts assembled by pomgen
# The same value can also be specified by setting the environment variable
# POMGEN_JAR_CLASSIFIER - the environment variable takes precedence over the
# value set in this cfg file
# Default value: ""
jar_classifier=
```


### transitives_versioning_mode

Please see [more information about transitives versioning](docs/ci.md#using-a-different-version-increment-mode-for-transitives).


### override_file_paths

[rules_jvm_external](https://github.com/bazelbuild/rules_jvm_external#overriding-generated-targets) allows to override dependencies at runtime. pomgen provides an equivalent override mechanism: use `override_file_paths` in the `[general]` section of .pomgenrc file. The value of `override_file_paths` is one or more paths (comma-separated) to .bzl files, containing a dependency -> overriden dependency mapping.

See [this example](examples/java/dep-overrides).


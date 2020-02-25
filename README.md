# pomgen

## Overview

The set of scripts in this repository provides a solution for:
 - Generating pom.xml files for jars built built by Bazel's ```java_library``` rule
 - Uploading the pom.xmls and jars to a Maven Artifact Repository such as Nexus (or installing them into the local Maven Repository at ~/.m2/repository)

## Setup

 - For each Maven Artifact producing Bazel Package, a [BUILD.pom](example/healthyfoods/fruit-api/MVN-INF/BUILD.pom) file defines Maven specific metadata
 - A special [marker file](example/healthyfoods/MVN-INF/LIBRARY.root) groups one or more Maven Artifacts into a Library

## Bazel Package References

The BUILD file of a Maven Artifact producing Bazel Package may obviously reference other Bazel Packages in the repository. pomgen will follow these references and generate pom.xmls for all referenced Bazel Packages. 

## Change tracking

pomgen can track whether the content of a Bazel Package has changed since it was last released. Generated poms reference the previously released Maven Artifact if no change is detected.

## Example

Please see the [pomgen example](example/README.md) to see how pomgen works.

## External Dependencies

- Python 3 is required and must be in your PATH
- You need to install [lxml](https://lxml.de): pip install --user lxml
- Everything has been testing with Bazel 1.0.  Other Bazel versions may work.

## Running pomgen in your own repository

Reference this repository in your `WORKSPACE` file using Bazel's `git_repository` rule:

```
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

git_repository(
    name = "pomgen",
    remote = "https://github.com/salesforce/pomgen.git",
    commit = "<git-commit-sha>"
)
```

You can then run Bazel commands [as documented](example/README.md), for example:

```
bazel run @pomgen//maven -- -a pomgen,install
```

## Configuration

Some pomgen behavior is driven by an optional configuration file `.pomgenrc`. pomgen looks for this file at the root of the repository it is running in.

The file format is:

```
[general]
# Path to the pom template, used when generating pom.xml files for jar artifacts
# Default value: config/pom_template.xml
pom_template_path=

# Path to the file that lists external dependencies - multiple files are supported, comma-separated
# Default value: WORKSPACE
# Example value: path/to/file1,path/to/file2
external_dependencies_path=

[crawler]
# A list of path prefixes that are not crawled by pomgen.  Any dependency
# that starts with one of the strings returned by this method is skipped 
# and not processed (and not included in the generated pom.xml).
# These dependencies are similar to Maven's "provided" scope: if they are
# needed at runtime, it is expected that the final runtime assembly
# contains them.
# Default value: ""
# Example value: projects/protos/,
excluded_dependency_paths=

[artifact]
# Paths not considered when determining whether an artifact has changed
# Default value: src/test,
excluded_relative_paths=

# File names not considered when determining whether an artifact has changed
# Default value: .gitignore,
excluded_filenames=

# Ignored file extensions when determining whether an artifact has changed
# Default value: .md,
excluded_extensions=
```

Running pomgen with `--verbose` causes the current config to be echoed.
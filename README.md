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

- [Python 2.7](https://github.com/salesforce/pomgen/issues/1) is required and must be in your PATH
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
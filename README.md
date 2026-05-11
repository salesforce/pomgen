# poppy (aka pomgen v3)

[![ci](https://github.com/salesforce/pomgen/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/salesforce/pomgen/actions/workflows/ci.yml)

:octocat: Please do us a huge favor. If you think this project could be useful for you, now or in the future, please hit the **Star** button at the top. That helps us advocate for more resources on this project. Thanks!


## Overview

`poppy` is an extensible package manager manifest generator for Bazel-based projects.

It currently supports Java (jars), Python (wheels) and JavaScript (npm packages).

### What problems does poppy solve?

TODO

### What's up with the name?

Originally this project was called `pomgen` because it was Java and pom.xml specific. But as we added Python support, we needed a new name. We picked `poppy` because it starts with po(m.xml) and ends with py(thon). The repository is still called `pomgen`, we may rename it at some point.

## Using poppy

See our examples to get started.

### Running poppy in your own repository

Reference this repository in your `WORKSPACE` file using Bazel's `git_repository` rule:

```
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

git_repository(
    name = "pomgen",
    remote = "https://github.com/salesforce/pomgen.git",
    commit = "<current master HEAD commit-sha>"
)
```
The `master` branch is always releasable - use the current `HEAD` commit.

You can then run pomgen commands [see the example](examples/java/hello-world/README.md), for example:

```
bazel run @poppy//package/maven -- -a pomgen,install
```

### CI setup

[This document](docs/ci.md) goes over the CI setup.

### Usage Requirements

- Bazel, through [bazelisk](https://github.com/bazelbuild/bazelisk)
- Python 3 is required and must be configured as a toolchain or available in your $PATH

### Java

- External Maven Central/Nexus dependencies **must** be managed using [rules_jvm_external](https://github.com/bazelbuild/rules_jvm_external)'s `maven_install` rule
- Artifacts **must** be [pinned](https://github.com/bazelbuild/rules_jvm_external#pinning-artifacts-and-integration-with-bazels-downloader), because pomgen parses the pinned artifacts' json file(s)
  - The location of all pinned artifact json files must be declared in the pomgen [config file](#configuration) by setting `maven_install_paths`

### Python

TODO

### JavaScript

TODO

## poppy development

### Linting

pomgen uses [ruff](https://github.com/astral-sh/ruff). Follow the installation instructions, then run:

```
ruff check src tests
```

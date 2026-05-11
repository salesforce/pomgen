# poppy (aka pomgen v3)

[![ci](https://github.com/salesforce/pomgen/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/salesforce/pomgen/actions/workflows/ci.yml)

:octocat: Please do us a huge favor. If you think this project could be useful for you, now or in the future, please hit the **Star** button at the top. That helps us advocate for more resources on this project. Thanks!


## Overview

`poppy` is a package manager manifest generator for Bazel-based projects.

It supports Java (jars), Python (wheels), JavaScript (npm packages) and can be extended to support additional manifest formats, package managers, languages.

### Why?

Bazel is generally used for building large repositories ("monorepo"). In such repositories, dependencies are built from source and always at the latest version. In an ideal world, all dependencies and all their consumers exist in the same repository. `poppy` is for the non-ideal world case, where some consumers exist outside of the Bazel-built repository. In this scenario, dependencies have to be shared with the outside via a package manager. `poppy` is the translation layer between Bazel and the package manager.

### Features

`poppy` provides the following high level features:

- package manager metadata for Bazel-built artifacts
- grouping of related artifacts into a library with a tracked version
- generation of package manager specific manifest file (for example pom.xml)
- convenience wrappers of package manager specific tooling to publish libraries
- supports many libraries with dependencies on each other
- change detection to avoid publishing when a library has not changed
- query capabilities to understand library structure
- extensible - can support different package managers / languages

### What's up with the name?

Originally this project was called `pomgen` because it was Java and pom.xml specific. As we added Python support, we needed a new name. We picked `poppy` because it starts with po(m.xml) and ends with py(thon). The repository is still called `pomgen`, we may rename it at some point. Got a better idea for a name? We thought you would - file an issue!

## Using poppy

The best way to learn about `poppy` is to explore the [examples](examples) and the [docs](docs).

### Running poppy in your own repository

Use `git_repository` and specificy the latest commit of the `master` branch. The `master` branch is always releasable.

In your `MODULE.bazel` file, load `git_repository` is you do not have it already:
```
git_repository = use_repo_rule(
    "@bazel_tools//tools/build_defs/repo:git.bzl",
    "git_repository",
)
```

Then add:
```
git_repository(
    name = "poppy",
    commit = "<latest commit from master branch>",
    remote = "https://github.com/salesforce/pomgen.git",
)
```

If everything is setup correcty, this command should succeed:
```
bazel run @poppy//:info
```

### CI setup

[This document](docs/ci.md) goes over the CI setup.

### Usage Requirements

- Your project must use Bazel
- Python 3 is required and must be configured as a Bazel Toolchain or available in your $PATH

## Development

### Linting

poppy uses [ruff](https://github.com/astral-sh/ruff). Follow the installation instructions, then run:

```
ruff check src tests
```

# Packaging jars

This script augments jars with their required pom.xmls and installs them into `~/m2/repository`, the standard location where other Java build tools (like [Maven](https://maven.apache.org)) will look for them. Optionally, the jars can also be uploaded to a Nexus-based package manager.

## Usage

### Install

`bazel run @poppy//package/maven -- -a pomgen,build,install -l path/to/library/root`

The command above will generated poms and install all jars that are part of the library pointed to by `-l`, and its transitive libraries, into ~/m2/repository. 

Since the `build` action (`-a` stands for action) is specified, the script will also use bazel to build all jars first.

Example invocation:

```
bazel run @poppy//package/maven -- -a pomgen,build,install -l examples/java/hello-world/juicer
```

### Deploy

The `deploy_all` action can be used instead of `install` above - the script will then upload the jars to a Nexus server. Set the `REPOSITORY_URL` environment variable to specify the server hostname.

For details on all arguments and options that may be specified, pass in `-h` or look at the [top of the script](maven.sh).

## External Dependencies

The following executables must be in $PATH:
- `mvn`
- `xmllint`

External Central/Nexus dependencies (jars) must be managed using [rules_jvm_external's maven_install](https://github.com/bazel-contrib/rules_jvm_external) rule.
Artifacts must be pinned, because poppy processes the pinned files.

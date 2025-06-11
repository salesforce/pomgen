# Miscellaneous scripts

## [extdeps_pomgen.py](extdeps_pomgen.py)

This script generates a single pom.xml that contains external (Maven Central/Nexus) dependencies. By default, it reads and processes all external dependencies that pomgen knows about.

To run:

```
bazel run @poppy//misc:extdeps
```

It is also possible to generate a custom pom.xml by passing a newline delimited list of dependenies to include in the pom.xml, to stdin:

```
echo -e "@maven//:org_antlr_ST4\n @maven//:com_google_guava_guava" | bazel run @poppy//misc:extdeps -- --stdin
```

To see all supported arguments, run:

```
bazel run @poppy//misc:extdeps -- --help
```

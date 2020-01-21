# Miscellaneous scripts

## [extdeps_pomgen.py](extdeps_pomgen.py)

This script generates a single pom.xml that contains external dependencies from Nexus. By default, it reads and processes all external Nexus dependencies that Bazel knows about.

To run:

```
bazel run @pomgen//misc:extdeps
```
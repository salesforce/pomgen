# Miscellaneous scripts

## [all_third_party_deps_pom.py](all_third_party_deps_pom.py)

This script generates a single pom.xml that contains all declared external dependencies.

To run:

```
bazel run @pomgen//misc:alldeps
```
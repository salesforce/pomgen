# Examples based goldfiles

This location contains the pom.xmls and related files generated by pomgen for the [examples](../examples) directory tree.

This makes it easy to detect fundamental changes in how pom files are generated that may not be caught by tests.

To updated the goldfiles, run from the root of this repository:

```
bazel run //:pomgen -- --package examples --destdir tests/examples_goldfiles
```

Then `git status` and `git diff` to see if anything/what changed.

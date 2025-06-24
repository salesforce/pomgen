# 111

This example shows that a Python project may be organized using Bazel's [1:1:1](https://bazel.build/basics/dependencies#using_fine-grained_modules_and_the_111_rule) rule.

Note that this works well for Python projects because the wheel file construction is external to Bazel. On the other hand, this doesn't work well for Java based projects because the jar file building is done by Bazel (and so with 1:1:1 we'd end up with too many jar files - they would have to be merged into a single jar before being uploaded to the package manager).


## The pyproject.toml file

Run this command:

```
bazel run @poppy//package/py -- -l examples/python/111 -a gen
```

Note [111_mode is enabled](md/pyproject.in) and that the child Bazel packages do not define any Poppy related metadata - dependencies declared in child Bazel packages' BUILD.bazel files are "pushed up" to, and included in, the `pyproject.toml` file generated for the `111` project.

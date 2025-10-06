# 1:1:1

This example shows a Python project using Bazel's [1:1:1](https://bazel.build/basics/dependencies#using_fine-grained_modules_and_the_111_rule) structure of "one BUILD file per Bazel package". Why is this interesting? Because the `1:1:1` structure is a common layout when using Bazel, especially when using [Gazelle](https://github.com/bazel-contrib/bazel-gazelle) to generate BUILD files. However, when generating manifests and artifacts for a package manager, we typically do not want to generate at the granularity of the Bazel package level but instead at the "project level" - Poppy handles this translation.


## Looking around

This example consists of 2 libraries, [communicator](communicator) and [computer](computer).
- `communicator` - has modules [phone](communicator/phone) and [caller](communicator/caller). The phone module has [111 mode enabled](communicator/phone/md/pyproject.in): `generation_mode` is set to `dynamic_111`. The `caller` module depends on the `phone` module.
- `computer` - has modules [amiga](computer/amiga) and [user](computer/user). Both modules have 111 mode enabled. The `user` module depends on the `amiga` module.
- Library dependencies: `communicator` depends on `computer`; this link exists bcause `phone` depends on `amiga` [here](communicator/phone/src/phone/emulator/BUILD).

The following `poppy` command shows how both libraries are related:

```
bazel run //:query -- --package examples/python/111/communicator --library_release_plan_tree

examples/python/111/communicator ++ 2.0.1
  examples/python/111/computer ++ 1.0.1

++ artifact has never been released
```


## About 1:1:1 mode

Support for `1:1:1` package structure must be set explicitly in the manifest file: `generation_mode = "dynamic_111"` [example](communicator/phone/md/pyproject.in).
Additionally, the manifest file must specify an "aggregation" target that has as dependencies all child `1:1:1` targets, in that example linked below that is configured by `target_name = "venv"`. For Python, this works well with a `venv` target. Note that if the `venv` target includes tests, those should be excluded explicitly (in the linked example, that is done using `excluded_dependency_paths = ["tests"]`.
Finally, the module structure must follow the modern Python project structure with top level `src` and `tests` directories.


## The 1:1:1 manifest

The generated manifest (pyproject.toml) aggregates all dependencies from child Bazel packages if they are:
- External (pip) dependencies
- Source dependencies that point outside of the 1:1:1 module

As an example, generate the `communicator` library manifest files:

```
bazel run //:gen -- --package examples/python/111/communicator --destdir /tmp/py
```

Since `communicator` depends on `computer`, and each library has 2 modules, 4 manifests are generated.

The `communicator/phone` manifest at `/tmp/py/examples/python/111/communicator/phone/pyproject.toml` lists these dependencies:

- `uvicorn[standard]>=0.34.0` brought in through [communicator/phone/src/phone/ringtone/BUILD](communicator/phone/src/phone/ringtone/BUILD)

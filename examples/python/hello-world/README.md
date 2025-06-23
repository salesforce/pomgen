# Hello Python!

One way to publish Python projects to a package manager is to create a [pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml) file that `python3 -m build` reads to generate the final wheel package. 

This is what Poppy provides: it generates a `pyproject.toml` file based on the content of the specified metadata and the Bazel `BUILD` files.


## Metadata

The metadata for this project is defined undet the [md](md) directory.

Note that the version defined in the [pyproject.in file](md/pyproject.in) references a timestamp using the syntax: `${timestamp:<format-string>}`, for example:
```
version = "0.0.1.dev${timestamp:%Y%m%d%H%M%S}",
```

This can be useful in CI when a unqiue version is required for every package upload.


## Packaging
```
bazel run @poppy//package/py -- -l examples/python/hello-world -a gen,build
```
The above command will generate `examples/python/hello-world/pyproject.toml` and build a `.whl` file under `examples/python/hello-world/dist`.

There are 2 steps:
  - The `gen` action generates the pyroject.toml file into `bazel-bin`
  - The `build` action copies it into the source tree, into the project directory folder, and runs `python3 -m build` on the project directory

If the environment variable `GLOBAL_DIST_DIR` is set, the content of the `dist` dir is copied to the directory that `GLOBAL_DIST_DIR` points to. This can be useful in CI.

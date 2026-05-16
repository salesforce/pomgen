# Building wheels

This script builds Python wheels with code and generated `pyproject.toml` manifests.

## Usage

Run the following command to generated installable wheels for all modules that are part of the given library, including all transitive libraries:

```
bazel run @poppy//package/py -- -l path/to/library/root -a gen,build
```

For example, to generate wheels for the `hello-word` library:
```
bazel run @poppy//package/py -- -l examples/python/hello-world -a gen,build
```

If you are using an internal PyPI registry, you may have to set `REQUESTS_CA_BUNDLE` to point to the right cert to use.

All artifacts including the wheels are built into the source tree. Set the environment variable `GLOBAL_DIST_DIR` to a directory to copy the wheels into after they have been built - this can be useful for CI setups.

For example, with `export GLOBAL_DIST_DIR=/tmp/dist`, after running the package cmd for the `hello-world` library:

```
$ ls /tmp/dist 
computer-0.0.2-py3-none-any.whl	greeter-0.0.2-py3-none-any.whl
computer-0.0.2.tar.gz		greeter-0.0.2.tar.gz
```

## External Dependencies

The following executables must be in $PATH:

- python3

Additionally, you need the `build` module:

```
pip3 install build
```

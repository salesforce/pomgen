# Hello Python!

One way to publish Python projects to a package manager is to create a [pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml) file that `python3 -m build` reads to generate the final wheel package. 

This is what Poppy provides: it generates a `pyproject.toml` file based on the content of the specified metadata and the Bazel `BUILD` files.


## Looking around

This example project has a single library with 2 modules, [greeter](greeter) and [computer](computer); greeter depends on computer.


## Running

```
bazel run examples/python/hello-world/greeter:main
Hello World!
```


## Metadata

The metadata for this project is defined under the `md` directories:

- [md](md): this directory contains only a marker file to signal that this is the root of the library. A library may contain one or more modules (greeter and computer in this example). Poppy processes all modules that are part of the same library (under the same library root directory) together.
- [greeter/md](greeter/md): metadata for the greeter module
- [computer/md](computer/md): metadata for the computer module

The [BUILD file in the greeter module](greeter/BUILD) references the [computer Bazel package](computer) - this dependency will be reflected in the `dependencies` of the generated pyproject.toml for `greeter`.
The [computer target](computer/BUILD) depends on an external dependency, `@examples_pip//uvicorn`. This dependency will be included in the generated pyproject.toml file for `computer`.


Note that the version defined in the pyproject.in files may use a timestamp pattern that is filled in when the pyproject.toml file is generated: `${timestamp:<format-string>}`, for example:
```
version = "0.0.1.dev${timestamp:%Y%m%d%H%M%S}",
```

This can be useful in CI when a unqiue version is required for every package upload.


## Packaging

### About the required directory structure

The generated `pyproject.toml` file (see below) requires there to be a `src` directory that contains the python files to package. The pyproject file also specifies `tool.setuptools.packages.find`, which means that it will look for `packages`, not lose source files in the source directory. Therefore the `src` dir needs to contain a package directory. See the structure of the [greeter](greeter) and [computer](computer) projects.


### Building the wheels

You need the `build` module; if you don't have it yet install it with:
```
pip3 install build
```

Run the following Poppy command to generate the manifests (the `gen` action) and generate the wheels for the `hello-world` library.

```
bazel run @poppy//package/py -- -l examples/python/hello-world -a gen,build
```
The above command will generate 2 pyproject.toml files:

- `examples/python/hello-world/greeter/pyproject.toml` and
- `examples/python/hello-world/computer/pyproject.toml`

Additionally, the `dist` directory contains the wheel files:
- `examples/python/hello-world/greeter/dist/greeter-0.0.1-py3-none-any.whl`
- `examples/python/hello-world/computer/dist//computer-0.0.1-py3-none-any.whl`


## Testing the wheels locally

Now let's install the wheels to confirm they work.

First, create a virtual env:
```
poppy_root=$(pwd)
cd /tmp
python3 -m venv test_venv
source test_venv/bin/activate
```

Install the wheels:
```
pip install $poppy_root/examples/python/hello-world/computer/dist/computer-0.0.3-py3-none-any.whl
pip install $poppy_root/examples/python/hello-world/greeter/dist/greeter-0.0.2-py3-none-any.whl
```

Run the greeter:
```
python3 -c "from greeter import greeter; print(greeter.get_greeting())"
```

# Creating a Local NPM Package

To build and create a local installable npm package for testing:

## Build the library

```
bazel build examples/js/hello-world/...
```

## Generate the package.json files

```
bazel run //:gen -- --package examples/js/hello-world --destdir bazel-bin
```

## Copy the generated package.json files into the package structure

```
chmod u+w bazel-bin/examples/js/hello-world/greeter-constants/pkg/package.json
cp bazel-bin/examples/js/hello-world/greeter-constants/package.json bazel-bin/examples/js/hello-world/greeter-constants/pkg/package.json

chmod u+w bazel-bin/examples/js/hello-world/greeter-lib/pkg/package.json
cp bazel-bin/examples/js/hello-world/greeter-lib/package.json bazel-bin/examples/js/hello-world/greeter-lib/pkg/package.json

chmod u+w bazel-bin/examples/js/hello-world/greeter/pkg/package.json
cp bazel-bin/examples/js/hello-world/greeter/package.json bazel-bin/examples/js/hello-world/greeter/pkg/package.json
```

## Create the tarball

```bash
mkdir -p /tmp/npm-packages
npm pack bazel-bin/examples/js/hello-world/greeter-constants/pkg --pack-destination /tmp/npm-packages

npm pack bazel-bin/examples/js/hello-world/greeter-lib/pkg --pack-destination /tmp/npm-packages

npm pack bazel-bin/examples/js/hello-world/greeter/pkg --pack-destination /tmp/npm-packages
```

## Testing the Package from Scratch

Create a new test project from scratch. Note: since `greeter-lib` depends on `greeter-constants`, both packages must be installed together.

```bash
mkdir /tmp/test-greeter && cd /tmp/test-greeter
```

```bash
npm init -y
```

Install both packages:

```bash
npm install /tmp/npm-packages/greeter-constants-1.2.3.tgz
npm install /tmp/npm-packages/greeter-lib-1.2.3.tgz
npm install /tmp/npm-packages/greeter-1.2.3.tgz
```

Create a test file:

```bash
cat > test.js << 'EOF'
require('greeter').default;
EOF
```

Run the test:

```bash
node test.js
```

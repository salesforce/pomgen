# Creating a Local NPM Package

To build and create a local installable npm package for testing:

## Build the library

```
bazel build examples/js/hello-world/...
```

## Generate the package.json files and project directories

```
bazel run @poppy//package/npm -- -l examples/js/hello-world -a gen,install
```

## Create the tarball

```bash
npm pack /tmp/npm-packages/greeter-constants --pack-destination /tmp/npm-packages
npm pack /tmp/npm-packages/greeter-lib --pack-destination /tmp/npm-packages
npm pack /tmp/npm-packages/greeter --pack-destination /tmp/npm-packages
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

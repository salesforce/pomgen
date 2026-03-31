# Creating a Local NPM Package

To build and create a local installable npm package for testing:

## Packaging greeter-lib

### 1. Build the package with Bazel

First, create the package structure at:
`bazel-bin/examples/js/hello-world/greeter-lib/pkg`

```bash
bazel build //examples/js/hello-world/greeter-lib:pkg
```

### 2. Copy the packaging package.json

Bazel outputs are read-only, so first make the file writable, then copy the package.json file from the `packaging` directory:

```bash
chmod u+w bazel-bin/examples/js/hello-world/greeter-lib/pkg/package.json
cp examples/js/hello-world/greeter-lib/packaging/package.json bazel-bin/examples/js/hello-world/greeter-lib/pkg/package.json
```

### 3. Create the tarball

```bash
npm pack bazel-bin/examples/js/hello-world/greeter-lib/pkg --pack-destination /tmp
```

This creates `/tmp/greeter-lib-1.0.0.tgz`.

## Packaging greeter-constants

### 1. Build the package with Bazel

```bash
bazel build //examples/js/hello-world/greeter-constants:pkg
```

### 2. Copy the packaging package.json

Bazel outputs are read-only, so first make the file writable, then copy the package.json file from the `packaging` directory:

```bash
chmod u+w bazel-bin/examples/js/hello-world/greeter-constants/pkg/package.json
cp examples/js/hello-world/greeter-constants/packaging/package.json bazel-bin/examples/js/hello-world/greeter-constants/pkg/package.json
```

### 3. Create the tarball

```bash
npm pack bazel-bin/examples/js/hello-world/greeter-constants/pkg --pack-destination /tmp
```

This creates `/tmp/greeter-constants-1.0.0.tgz`.

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
npm install /tmp/greeter-constants-1.0.0.tgz /tmp/greeter-lib-1.0.0.tgz
```

Create a test file:

```bash
cat > test.js << 'EOF'
const greet = require('greeter-lib').default;
console.log(greet());
EOF
```

Run the test:

```bash
node test.js
```

## Package Structure

The built package contains:
- `package.json` - package metadata and dependencies
- `src/*.js` - compiled JavaScript files
- `src/*.d.ts` - TypeScript type definitions

## Alternative Approach: Using a Temporary Directory

Instead of modifying the read-only Bazel output in place, you can copy to a temporary directory:

### For greeter-lib

```bash
TEMP_DIR=$(mktemp -d)
cp -r bazel-bin/examples/js/hello-world/greeter-lib/pkg $TEMP_DIR/pkg
chmod -R u+w $TEMP_DIR/pkg
cp examples/js/hello-world/greeter-lib/packaging/package.json $TEMP_DIR/pkg/package.json
npm pack $TEMP_DIR/pkg --pack-destination /tmp
rm -rf $TEMP_DIR
```

### For greeter-constants

```bash
TEMP_DIR=$(mktemp -d)
cp -r bazel-bin/examples/js/hello-world/greeter-constants/pkg $TEMP_DIR/pkg
chmod -R u+w $TEMP_DIR/pkg
cp examples/js/hello-world/greeter-constants/packaging/package.json $TEMP_DIR/pkg/package.json
npm pack $TEMP_DIR/pkg --pack-destination /tmp
rm -rf $TEMP_DIR
```

This approach avoids modifying Bazel's output directory and provides better isolation.

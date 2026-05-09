# Hello TypeScript!

This example has a single [hello-world library](pack/LIBRARY.root) with 3 modules:

- [greeter](greeter) depends on
- [greeter-lib](greeter-lib) depends on
- [greeter-constants](greeter-contants)


Greeter comes with a runnable target:

```
bazel run examples/js/hello-world/greeter/greeter_bin
```


## The package.json Manifest

Generate `package.json` files for the 3 modules:

```
bazel run //:gen -- --package examples/js/hello-world --destdir /tmp
```

The generated `package.json` contains information from 3 places:

- The poppy module manifest files [ref](greeter-lib/pack/package.in)
- The static package.json that lives at the project root [ref](greeter-lib/package.json)
- The dependencies in the BUILD file (for ex figlet) [ref](greeter-lib/BUILD)

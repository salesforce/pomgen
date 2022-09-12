# Compilation time only deps should not be evaluated by pomgen

There are some dependencies that are needed only at compilation time, like for example Lombok.
This kind of dependencies can be managed differently by Bazel adding the attribute `neverlink = 1` to `java_library`.
Most likely those dependencies won't have a `BUILD.pom` file, so they have to be ignored by `pomgen`.

### Try this example

From the root of the repository:

```
bazel build examples/dependency-management/...
```

```
bazel run @pomgen//maven -- -a pomgen,install -t examples/dependency-management
```

Now look under your `$HOME/.m2/repository`:

The usual `jar` packaging pom is at:
`com/pomgen/depman/example/juicer/3.0.0-SNAPSHOT/juicer-3.0.0-SNAPSHOT.pom`

The dependency management pom (`pom` packaging) is at:
`com/pomgen/depman/example/juicer.depmanagement/3.0.0-SNAPSHOT/juicer.depmanagement-3.0.0-SNAPSHOT.pom`


The `<dependencyManagement>` in the dependency management pom can be used (imported) the following way:

```
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.pomgen.depman.example</groupId>
            <artifactId>juicer.depmanagement</artifactId>
            <version>3.0.0-SNAPSHOT</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
<dependencyManagement>
```

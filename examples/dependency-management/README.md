# Dependency Management POM Example

This examples shows how pomgen can optionally generate a dependencyManagement "companion" pom. This pom file is generated in addition to the regular pom.xml, when the attribute `generate_dependency_management_pom` is to to `True` in the [BUILD.pom file](juicer/MVN-INF/BUILD.pom).

The dependency management pom contains a `<dependencyManagement>` section with the transitive closure of all dependencies of the artifact it was generated for. It uses the `artifact_id` specified in the BUILD.pom file, suffixed with `.depmanagement`.


### Try this example

From the root of the repository:

```
bazel build examples/dependency-management/...
```

```
bazel run @poppy//package/maven -- -a pomgen,install -l examples/dependency-management
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

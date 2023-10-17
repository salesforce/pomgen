### Overridding dependencies

Add an extra parameter `override_file_paths` in [general] section of the .pomgenrc file indicating the path to .bzl files containing the mapping `dep: overridden_dep`.

While parsing the pinned json files pomgen will override the deps reading the override_file_paths. It will override the direct dependency as well as the transitives.

In the current overide.bzl file - `javax.annotation:javax.annotation-api` dependency will be overridden with `@jakarta//:jakarta_annotation_jakarta_annotation_api`

There is a target `override_dep_test` in the BUILD which depends on `@javax//:javax_validation_validation_api` and `@org_apache//:org_apache_jclouds_jclouds_core`

Most of javax libraries are now migrated to their jakarta equivalent. Also, `@org_apache//:org_apache_jclouds_jclouds_core` depends on `javax.validation:validation-api` i.e. its transitive is also migrated to the jakarta equivalent.

##### Without `override_file_paths` the result of pomgen will be 
```xml
<dependencies>
    <dependency>
        <groupId>javax.validation</groupId>
        <artifactId>validation-api</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
    <dependency>
        <groupId>org.apache.jclouds</groupId>
        <artifactId>jclouds-core</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>

    <!-- The transitives of the dependencies above -->

    <dependency>
        <groupId>javax.annotation</groupId>
        <artifactId>javax.annotation-api</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
</dependencies>
```

##### With `override_file_paths` the result of pomgen will be 
```xml
<dependencies>
    <dependency>
        <groupId>jakarta.validation</groupId>
        <artifactId>jakarta.validation-api</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
    <dependency>
        <groupId>org.apache.jclouds</groupId>
        <artifactId>jclouds-core</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>

    <!-- The transitives of the dependencies above -->
    
    <dependency>
        <groupId>jakarta.annotation</groupId>
        <artifactId>jakarta.annotation-api</artifactId>
        <version>*</version>
        <exclusions>
            <exclusion>
                <groupId>*</groupId>
                <artifactId>*</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
</dependencies>
```
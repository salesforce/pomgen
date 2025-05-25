"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from common import pomgenmode
from crawl import buildpom
from crawl import dependency
import unittest


class DependencyTest(unittest.TestCase):

    def test_external_dependency__three_coordinates(self):
        """
        Ensures we can create a Dependency instance from a maven coord.
        """
        artifact = "com.google.guava:guava:20.0"
        dep = dependency.new_dep_from_maven_art_str(artifact, "name")
        self.assertEqual("com.google.guava", dep.group_id)
        self.assertEqual("guava", dep.artifact_id)
        self.assertEqual("20.0", dep.version)
        self.assertIsNone(dep.classifier)
        self.assertEqual("jar", dep.packaging)
        self.assertIsNone(dep.scope)

    def test_external_dependency__four_coordinates(self):
        """
        Ensures we can create a Dependency instance from a maven coord.
        """
        artifact = "com.grail.log-tokenizer:core-log-tokenizer-api:jar:0.0.21"
        dep = dependency.new_dep_from_maven_art_str(artifact, "name")
        self.assertEqual("com.grail.log-tokenizer", dep.group_id)
        self.assertEqual("core-log-tokenizer-api", dep.artifact_id)
        self.assertEqual("0.0.21", dep.version)
        self.assertIsNone(dep.classifier)
        self.assertEqual("jar", dep.packaging)
        self.assertIsNone(dep.scope)

    def test_external_dependency__five_coordinates(self):
        """
        Ensures we can create a Dependency instance from a maven coord.
        """
        artifact = "com.grail.servicelibs:dynamic-keystore-impl:jar:tests:2.0.39"
        dep = dependency.new_dep_from_maven_art_str(artifact, "name")
        self.assertEqual("com.grail.servicelibs", dep.group_id)
        self.assertEqual("dynamic-keystore-impl", dep.artifact_id)
        self.assertEqual("2.0.39", dep.version)
        self.assertEqual("tests", dep.classifier)
        self.assertEqual("jar", dep.packaging)
        self.assertIsNone(dep.scope)

    def test_external_dependency__marked_as_external(self):
        """
        Ensures the Dependency instance for an external dependency has the
        'external' boolean set as expected
        """
        artifact = "group:art:ver"
        dep = dependency.new_dep_from_maven_art_str(artifact, "name")
        self.assertTrue(dep.external)

    def test_external_dependency__references_artifact(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names.
        """
        artifact = "group:art:ver"
        dep = dependency.new_dep_from_maven_art_str(artifact, "bazel-name")
        self.assertTrue(dep.references_artifact)

    def test_external_dependency__names(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names.
        """
        artifact = "group:art:ver"
        dep = dependency.new_dep_from_maven_art_str(artifact, "maven")
        self.assertEqual("group:art", dep.maven_coordinates_name)
        self.assertEqual("@maven//:group_art", dep.bazel_label_name)
        self.assertEqual("group_art", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__none_name(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names.
        """
        artifact = "group:art:ver"
        dep = dependency.new_dep_from_maven_art_str(artifact, name=None)
        self.assertEqual("group:art", dep.maven_coordinates_name)
        self.assertEqual("group_art", dep.bazel_label_name)
        self.assertEqual("group_art", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__maven_install_name_with_leading_at(self):
        """
        Ensures we handle a maven_install_name with  leading "@".
        """
        artifact = "group:art:ver"
        dep = dependency.new_dep_from_maven_art_str(artifact, "@maven")
        self.assertEqual("group:art", dep.maven_coordinates_name)
        self.assertEqual("@maven//:group_art", dep.bazel_label_name)
        self.assertEqual("group_art", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__default_packaging(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names when packaging has a default value.
        """
        dep = dependency.ThirdPartyDependency(maven_install_name="name",
                                              group_id="group",
                                              artifact_id="art",
                                              version="1.0.0",
                                              packaging="jar")
        self.assertEqual("group:art", dep.maven_coordinates_name)
        self.assertEqual("@name//:group_art", dep.bazel_label_name)
        self.assertEqual("group_art", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__with_packaging(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names when packaging is specified.
        """
        artifact = "group:art:packaging:version"
        dep = dependency.new_dep_from_maven_art_str(artifact, "maven")
        self.assertEqual("group:art:packaging", dep.maven_coordinates_name)
        self.assertEqual("@maven//:group_art_packaging", dep.bazel_label_name)
        self.assertEqual("group_art_packaging", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__with_packaging_and_classifier(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names when packaging and classifier are set.
        """
        artifact = "group:art:pack:class:version"
        dep = dependency.new_dep_from_maven_art_str(artifact, "mvn")
        self.assertEqual("group:art:pack:class", dep.maven_coordinates_name)
        self.assertEqual("@mvn//:group_art_pack_class", dep.bazel_label_name)
        self.assertEqual("group_art_pack_class", dep.unqualified_bazel_label_name)

    def test_external_dependency__names__with_classifier_and_default_packaging(self):
        """
        Ensures the Dependency instance for an external dependency has expected
        names when packaging and classifier are set.
        """
        dep = dependency.ThirdPartyDependency(maven_install_name="name",
                                              group_id="group",
                                              artifact_id="art",
                                              version="1.0.0",
                                              classifier="class")
        self.assertEqual("group:art:jar:class", dep.maven_coordinates_name)
        self.assertEqual("@name//:group_art_class", dep.bazel_label_name)
        self.assertEqual("group_art_class", dep.unqualified_bazel_label_name)

    def test_external_dependency__unparsable_artifact(self):
        """
        Ensures that external dependency parsing fails when the entire artifact
        string is invalid.        
        """
        artifact = "group:artifact"
        with self.assertRaises(Exception) as ctx:
            dependency.new_dep_from_maven_art_str(artifact, "bazel-name")

        self.assertIn("cannot parse", str(ctx.exception))

    def test_external_dependency__unsupported_version_syntax(self):
        """
        Ensures that external dependency parsing fails when the version string 
        is invalid.
        """
        artifact = "org.glassfish.jersey.ext:jersey-bean-validation:"

        with self.assertRaises(Exception) as ctx:
            dependency.new_dep_from_maven_art_str(artifact, "bazel-name")

        self.assertIn("invalid version", str(ctx.exception))
        
    def test_source_dependency__from_artifact_definition__name(self):
        """
        Ensures the Dependency instance for a source dependency has expected
        names.
        """
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        package = "pack1"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version, bazel_package="p1")
        art_def = buildpom._augment_art_def_values(art_def, None, package, None, None, pomgenmode.DYNAMIC)

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertEqual("g1:a1", dep.maven_coordinates_name)
        self.assertIsNone(dep.bazel_label_name)

    def test_source_dependency__from_artifact_definition__default(self):
        """
        Ensures the Dependency instance for a source dependency looks right.
        """
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        package = "pack1"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version)
        art_def = buildpom._augment_art_def_values(art_def, None, package, None, None, pomgenmode.DYNAMIC)

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)
        self.assertEqual(version, dep.version)
        self.assertEqual(package, dep.bazel_package)
        self.assertFalse(dep.external)

    def test_source_dependency__from_artifact_definition__with_changes(self):
        """
        Ensures the Dependency instance for a source dependency looks right.

        Here we explicitly declare that the source has changed since it was
        last released.
        """        
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        package = "pack1"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version,
                                            bazel_package=package,
                                            requires_release=True,
                                            released_version="1.2.3",
                                            released_artifact_hash="123456789",
                                            bazel_target="t1")

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)
        self.assertEqual(version, dep.version)
        self.assertEqual(package, dep.bazel_package)
        self.assertFalse(dep.external)

    def test_source_dependency__from_artifact_definition__no_changes(self):
        """
        Ensures the Dependency instance for a source dependency looks right.

        Here we explicitly declare that the source has *NOT* changed since it 
        was last released.
        """        
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        released_version = "1.2.3"
        package = "pack1"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version,
                                            bazel_package=package,
                                            requires_release=False,
                                            released_version=released_version,
                                            released_artifact_hash="123456789",
                                            bazel_target="t1")

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertEqual(group_id, dep.group_id)
        self.assertEqual(artifact_id, dep.artifact_id)
        self.assertEqual(released_version, dep.version)
        self.assertEqual(package, dep.bazel_package)
        self.assertTrue(dep.external)

    def test_source_dependency__references_artifact__skip_pom_gen_mode(self):
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        released_version = "1.2.3"
        package = "pack1/pack2"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version,
                                            pom_generation_mode=pomgenmode.SKIP,
                                            bazel_package=package,
                                            requires_release=False,
                                            released_version=released_version,
                                            released_artifact_hash="123456789",
                                            bazel_target="t1")

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertFalse(dep.references_artifact)

    def test_source_dependency__references_artifact__dynamic_pom_gen_mode(self):
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        released_version = "1.2.3"
        package = "pack1/pack2"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version,
                                            pom_generation_mode=pomgenmode.DYNAMIC,
                                            bazel_package=package,
                                            requires_release=False,
                                            released_version=released_version,
                                            released_artifact_hash="123456789",
                                            bazel_target="t1")

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertTrue(dep.references_artifact)

    def test_source_dependency__references_artifact__template_pom_gen_mode(self):
        group_id = "g1"
        artifact_id = "a1"
        version = "1.1.0"
        released_version = "1.2.3"
        package = "pack1/pack2"
        art_def = buildpom.MavenArtifactDef(group_id, artifact_id, version,
                                            pom_generation_mode=pomgenmode.TEMPLATE,
                                            bazel_package=package,
                                            requires_release=False,
                                            released_version=released_version,
                                            released_artifact_hash="123456789",
                                            bazel_target="t1")

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertTrue(dep.references_artifact)

    def test_sort_order(self):
        """
        Verifies that sorting Dependency instances produces the desired 
        ordering: alphanumeric, monorepo artifacts first.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20.0", "name")
        dep2 = dependency.new_dep_from_maven_art_str("com.google.guava:zoouava:20.0", "name")
        art_def = buildpom.MavenArtifactDef("com.zoogle.guava", "art1", "1.0", bazel_package="p1")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep3 = dependency.new_dep_from_maven_artifact_def(art_def)
        art_def = buildpom.MavenArtifactDef("com.google.guava", "art1", "1.0")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep4 = dependency.new_dep_from_maven_artifact_def(art_def)
        
        lst = [dep3, dep2, dep1, dep4]
        lst.sort()
        self.assertIs(dep4, lst[0])
        self.assertIs(dep3, lst[1])
        self.assertIs(dep1, lst[2])
        self.assertIs(dep2, lst[3])

    def test_sort_order_includes_classifier__one_dep_without_classifier(self):
        """
        Ensures that the optional classifier of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:2.2.17", "name1")
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:idl:2.2.17", "name2")
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:aaa:2.2.17", "name3")

        lst = [dep1, dep2, dep3]
        lst.sort()
        self.assertIs(dep1, lst[0])
        self.assertIs(dep3, lst[1])
        self.assertIs(dep2, lst[2])

    def test_sort_order_includes_classifier__all_deps_with_classifier(self):
        """
        Ensures that the optional classifier of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:hhh:2.2.17", "name1")
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:zzz:2.2.17", "name2")
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:aaa:2.2.17", "name3")

        lst = [dep1, dep2, dep3,]
        lst.sort()
        self.assertIs(dep3, lst[0])
        self.assertIs(dep1, lst[1])
        self.assertIs(dep2, lst[2])

    def test_sort_order_includes_packaging__all_deps_with_packaging(self):
        """
        Ensures that the optional packaging of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar2:classifier:2.2.17", "name1")
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar3:classifier:2.2.17", "name2")
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar1:classifier:2.2.17", "name3")

        lst = [dep1, dep2, dep3,]
        lst.sort()
        self.assertIs(dep3, lst[0])
        self.assertIs(dep1, lst[1])
        self.assertIs(dep2, lst[2])

    def test_sort_order_includes_packaging__one_dep_without_packaging(self):
        """
        Ensures that the optional packaging of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar2:2.2.17", "name1")
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:2.2.17", "name2")
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar1:2.2.17", "name3")

        lst = [dep1, dep2, dep3,]
        lst.sort()
        self.assertIs(dep2, lst[0])
        self.assertIs(dep3, lst[1])
        self.assertIs(dep1, lst[2])

    def test_sort_order_includes_scope__all_deps_with_scope(self):
        """
        Ensures that the optional scope of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:hhh:2.2.17", "name1")
        dep1.scope = "s1"
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:hhh:2.2.17", "name2")
        dep2.scope = "s3"
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:hhh:2.2.17", "name3")
        dep3.scope = "s2"

        lst = [dep1, dep2, dep3,]
        lst.sort()
        self.assertIs(dep1, lst[0])
        self.assertIs(dep3, lst[1])
        self.assertIs(dep2, lst[2])

    def test_sort_order_includes_scope__all_deps_with_scope__no_classifier(self):
        """
        Ensures that the optional scope of an external dependency is
        included when sorting dependencies.
        """
        dep1 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:2.2.17", "name1")
        dep1.scope = "s1"
        dep2 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:2.2.17", "name2")
        dep2.scope = "s3"
        dep3 = dependency.new_dep_from_maven_art_str("com.grail.services:arthur-common-thrift-api:jar:2.2.17", "name3")
        dep3.scope = "s2"

        lst = [dep1, dep2, dep3,]
        lst.sort()
        self.assertIs(dep1, lst[0])
        self.assertIs(dep3, lst[1])
        self.assertIs(dep2, lst[2])

    def test_equals_hash_code(self):
        dep1 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20.0", "name")
        dep2 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20.0", "name")
        dep3 = dependency.new_dep_from_maven_art_str("com.google.guava22:guava:20.0", "name")
        s = set()
        s.add(dep1)
        s.add(dep2)
        s.add(dep3)

        self.assertEqual(dep1, dep2)

        self.assertEqual(2, len(s))
        self.assertTrue(dep1 in s)
        self.assertTrue(dep2 in s)
        self.assertTrue(dep3 in s)

    def test_equals_hash_code__default_packaging(self):
        dep1 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:jar:20.0", "name")
        dep2 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20.0", "name")
        s = set()
        s.add(dep1)
        s.add(dep2)

        self.assertEqual(dep1, dep2)
        self.assertEqual(1, len(s))
        self.assertTrue(dep1 in s)
        self.assertTrue(dep2 in s)

    def test_equals_ignores_version(self):
        dep1 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:20.0", "name")
        dep2 = dependency.new_dep_from_maven_art_str("com.google.guava:guava:100", "name")

        self.assertEqual(dep1, dep2)

    def test_copy(self):
        import copy
        dep = dependency.ThirdPartyDependency("name", "group", "artifact", "version", "classifier", "packaging", "scope") 

        dep_copy = copy.copy(dep)
        
        self.assertTrue(dep is dep)
        self.assertFalse(dep is dep_copy)
        self.assertEqual(dep, dep_copy)
        self.assertEqual("group", dep_copy.group_id)
        self.assertEqual("artifact", dep_copy.artifact_id)
        self.assertEqual("version", dep_copy.version)
        self.assertEqual("classifier", dep_copy.classifier)
        self.assertEqual("packaging", dep_copy.packaging)
        self.assertEqual("scope", dep_copy.scope)

    def test_bazel_buildable__external_dep(self):
        artifact = "com.google.guava:guava:20.0"

        dep = dependency.new_dep_from_maven_art_str(artifact, "name")

        self.assertFalse(dep.bazel_buildable)

    def test_bazel_buildable__source_dep__skip_pom_gen(self):
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.SKIP)

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertFalse(dep.bazel_buildable)

    def test_bazel_buildable__source_dep__dynamic_pom_gen(self):
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.DYNAMIC)

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertTrue(dep.bazel_buildable)

    def test_bazel_buildable__source_dep__template_pom_gen__pom_packaging(self):
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.TEMPLATE)
        art_def.custom_pom_template_content = "<packaging>pom</packaging>"

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertFalse(dep.bazel_buildable)

    def test_bazel_buildable__source_dep__template_pom_gen__other_packaging(self):
        art_def = buildpom.MavenArtifactDef("g1", "a1", "1.0")
        art_def = buildpom._augment_art_def_values(art_def, None, "pack1", None, None, pomgenmode.TEMPLATE)
        art_def.custom_pom_template_content = "<packaging>maven-plugin</packaging>"

        dep = dependency.new_dep_from_maven_artifact_def(art_def)

        self.assertTrue(dep.bazel_buildable)


if __name__ == '__main__':
    unittest.main()


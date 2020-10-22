"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
from common import pomgenmode
from config import exclusions
from crawl import bazel
from crawl import buildpom
from crawl import dependency
from crawl import pom
from crawl import workspace
import unittest

TEST_POM_TEMPLATE = """
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <groupId>${group_id}</groupId>
    <artifactId>${artifact_id}</artifactId>
    <version>${version}</version>
    <packaging>jar</packaging>

${dependencies}
</project>
"""

class PomTest(unittest.TestCase):

    def test_dynamic_pom__sanity(self):
        """
        Ensures that dynamic pom generation isn't totally broken.
        """
        ws = workspace.Workspace("some/path", """
  native.maven_jar(
    name = "aopalliance_aopalliance",
    artifact = "aopalliance:aopalliance:1.0",
  )
  native.maven_jar(
    name = "com_google_guava_guava",
    artifact = "com.google.guava:guava:20.0",
  )""", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        artifact_def = buildpom._augment_art_def_values(artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)

        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: ("@com_google_guava_guava//jar", "@aopalliance_aopalliance//jar", )
            _, _, deps = pomgen.process_dependencies()
            pomgen.register_dependencies(deps)
            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

            self.assertIn("""<groupId>g1</groupId>
    <artifactId>a2</artifactId>
    <version>1.2.3</version>
    <packaging>jar</packaging>""", generated_pom)
            
            self.assertIn("""<groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>20.0</version>
            <exclusions>
                <exclusion>
                    <groupId>*</groupId>
                    <artifactId>*</artifactId>
                </exclusion>
            </exclusions>""", generated_pom)

            aop_index = generated_pom.index("aopalliance")
            guava_index = generated_pom.index("guava")
            self.assertTrue(guava_index < aop_index) # deps are BUILD file order
        finally:
            bazel.query_java_library_deps_attributes = org_function

    def test_dynamic_pom__do_not_include_deps(self):
        """
        Tests the seldom used "include_deps = False".
        """
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.MavenArtifactDef("g1", "a2", "1.2.3",
                                                 include_deps=False)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, "")

        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: 1/0 # fails
            pomgen.process_dependencies()
            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

            self.assertNotIn("dependencies", generated_pom)
        finally:
            bazel.query_java_library_deps_attributes = org_function

    def test_dynamic_pom_genmode__goldfile(self):
        """
        Test goldfile mode with dynamic pom gen.
        """
        ws = workspace.Workspace("some/path", """
  native.maven_jar(
    name = "aopalliance_aopalliance",
    artifact = "aopalliance:aopalliance:1.0",
  )
  native.maven_jar(
    name = "com_google_guava_guava",
    artifact = "com.google.guava:guava:20.0",
  )""", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        artifact_def = buildpom._augment_art_def_values(artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)

        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)

        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: ("@com_google_guava_guava//jar", "@aopalliance_aopalliance//jar", )
            _, _, deps = pomgen.process_dependencies()
            pomgen.register_dependencies(deps)

            generated_pom = pomgen.gen(pom.PomContentType.GOLDFILE)

            self.assertIn("""<groupId>g1</groupId>
    <artifactId>a2</artifactId>
    <version>***</version>
    <packaging>jar</packaging>""", generated_pom)

            self.assertIn("""<groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>20.0</version>
            <exclusions>
                <exclusion>
                    <groupId>*</groupId>
                    <artifactId>*</artifactId>
                </exclusion>
            </exclusions>""", generated_pom)

            aop_index = generated_pom.index("aopalliance")
            guava_index = generated_pom.index("guava")
            self.assertTrue(guava_index > aop_index) # deps are sorted
        finally:
            bazel.query_java_library_deps_attributes = org_function

    def test_template_var_sub(self):
        """
        Verifies variable substitution in a pom template.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4",
            )""", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            logback_old_syntax #{ch_qos_logback_logback_classic.version}
            logback_new_syntax #{ch.qos.logback:logback-classic:version}
            monorepo artifact version #{version}""")

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("logback_old_syntax 1.4.4", generated_pom)
        self.assertIn("logback_new_syntax 1.4.4", generated_pom)
        self.assertIn("monorepo artifact version 1.2.3", generated_pom)

    def test_template_var_sub__monorepo_deps(self):
        """
        Verifies references to monorepo versions in a pom template.
        """
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.MavenArtifactDef("groupId", "artifactId", "1.2.3")
        srpc_artifact_def = buildpom.MavenArtifactDef("com.grail.srpc",
                                                      "srpc-api", "5.6.7")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            srpc #{com.grail.srpc:srpc-api:version}""")
        pomgen.register_all_dependencies(set([dependency.MonorepoDependency(srpc_artifact_def, bazel_target=None)]), set(), ())

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)
        
        self.assertIn("srpc 5.6.7", generated_pom)

    def test_template_var_sub__conflicting_gav__ext_and_BUILDpom(self):
        """
        Verifies error handling when gavs are conflicting between external deps
        and what is set in BUILD.pom files.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "name",
                artifact = "g:a:20",
            )""", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            srpc #{g:a:version}""")
        art = buildpom.MavenArtifactDef("g","a","1", bazel_package="a/b/c")
        d = dependency.MonorepoDependency(art, bazel_target=None)
        pomgen.register_all_dependencies(set([d]), set(), ())

        with self.assertRaises(Exception) as ctx:
            pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("Found multiple artifacts with the same groupId:artifactId", str(ctx.exception))
        self.assertIn("g:a", str(ctx.exception))

    def test_template_var_sub__multiple_ext_deps_with_same_gav(self):
        """
        Verifies that pomgen is ok with multiple external deps with the same
        gav. This is an edge case, where the WORKSPACE file defines 2 (or more)
        differnently named maven_jars, that all point back to the same artifact.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "name1",
                artifact = "g:a:20",
            )

            native.maven_jar(
                name = "name2",
                artifact = "g:a:20",
            )

        """, [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            srpc #{g:a:version}""")

        pomgen.gen(pom.PomContentType.RELEASE)

    def test_template_var_sub__multiple_ext_deps_with_same_ga_diff_vers(self):
        """
        Verifies that pomgen is NOT OK with multiple external deps with the same
        groupId/artifactId but with a different version (as this would break
        the #{<groupId>:<artifactId>:version} syntax).
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "name1",
                artifact = "g:a:20",
            )

            native.maven_jar(
                name = "name2",
                artifact = "g:a:21",
            )

        """, [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            srpc #{g:a:version}""")

        with self.assertRaises(Exception) as ctx:
            pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("Found multiple artifacts with the same groupId:artifactId", str(ctx.exception))
        self.assertIn("g:a", str(ctx.exception))

    def test_template_genmode__goldfile(self):
        """
        Verifies version omissions when genmode is GOLDFILE.
        """
        ws = workspace.Workspace("some/path", """
            native.maven_jar(
                name = "ch_qos_logback_logback_classic",
                artifact = "ch.qos.logback:logback-classic:1.4.4",
            )""", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        srpc_artifact_def = buildpom.maven_artifact("com.grail.srpc",
                                                    "srpc-api", "5.6.7")
        srpc_artifact_def = buildpom._augment_art_def_values(srpc_artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(srpc_artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            this artifact version #{version}
            logback #{ch.qos.logback:logback-classic:version}
            srpc #{com.grail.srpc:srpc-api:version}""")
        pomgen.register_all_dependencies(set([dependency.MonorepoDependency(srpc_artifact_def, bazel_target=None)]), set(), ())

        generated_pom = pomgen.gen(pomcontenttype=pom.PomContentType.GOLDFILE)

        self.assertIn("this artifact version ***", generated_pom)
        self.assertIn("logback 1.4.4", generated_pom)
        self.assertIn("srpc ***", generated_pom)

    def test_template__deps_config_setion_is_removed(self):
        """
        Verifies that the special dependency config section is removed
        from the pom template when it is processed.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
__pomgen.start_dependency_customization__
__pomgen.end_dependency_customization__
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__unencountered_deps(self):
        """
        Verifies that declared deps that are not crawled can be referenced
        using the pomgen.unencountered_deps property.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
__pomgen.start_dependency_customization__
            <dependency>
                <artifactId>art1</artifactId>
                <groupId>group1</groupId>
                <version>1.0.0</version>
                <exclusions>
                    <exclusion>
                        <artifactId>ea1</artifactId>
                        <groupId>eg1</groupId>
                    </exclusion>
                </exclusions>
            </dependency>
__pomgen.end_dependency_customization__
#{pomgen.unencountered_dependencies}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <artifactId>art1</artifactId>
                <groupId>group1</groupId>
                <version>1.0.0</version>
                <exclusions>
                    <exclusion>
                        <artifactId>ea1</artifactId>
                        <groupId>eg1</groupId>
                    </exclusion>
                </exclusions>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__crawled_bazel_packages(self):
        """
        Verifies that crawled bazel packages can be referenced using the 
        property pomgen.crawled_bazel_packages.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
#{pomgen.crawled_bazel_packages}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>c.s.sconems</groupId>
                <artifactId>abstractions</artifactId>
                <version>0.0.1</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)
        crawled_package = dependency.ThirdPartyDependency("name", "c.s.sconems", "abstractions", "0.0.1")
        pomgen.register_all_dependencies(set([crawled_package]), set(), ())

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__crawled_external_deps(self):
        """
        Verifies that crawled external deps can be referenced using the 
        property pomgen.crawled_external_dependencies.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
#{pomgen.crawled_external_dependencies}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>cg</groupId>
                <artifactId>ca</artifactId>
                <version>0.0.1</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)
        crawled_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_all_dependencies(set(), set([crawled_dep]), ())

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__crawled_external_deps__configured_exclusions(self):
        """
        Verifies that exclusions can be "attached" to crawled deps by
        declaring them in a dependency config section.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
__pomgen.start_dependency_customization__
            <dependency>
                <artifactId>ca</artifactId>
                <groupId>cg</groupId>
                <version>0.0.1</version>
                <classifier>c1</classifier>
                <exclusions>
                    <exclusion>
                        <artifactId>ea1</artifactId>
                        <groupId>zzz</groupId>
                    </exclusion>
                    <exclusion>
                        <artifactId>ea2</artifactId>
                        <groupId>aaa</groupId>
                    </exclusion>
                </exclusions>
            </dependency>
__pomgen.end_dependency_customization__
#{pomgen.crawled_external_dependencies}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>cg</groupId>
                <artifactId>ca</artifactId>
                <version>0.0.1</version>
                <classifier>c1</classifier>
                <exclusions>
                    <exclusion>
                        <groupId>aaa</groupId>
                        <artifactId>ea2</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>zzz</groupId>
                        <artifactId>ea1</artifactId>
                    </exclusion>
                </exclusions>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)
        crawled_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_all_dependencies(set(), set([crawled_dep]), ())

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__crawled_external_deps__configured_attributes(self):
        """
        Verifies that "classifier" and "scope" are correcly set in the generated
        pom.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
__pomgen.start_dependency_customization__
            <dependency>
                <artifactId>ca</artifactId>
                <groupId>cg</groupId>
                <version>0.0.1</version>
                <scope>test</scope>
                <classifier>sources</classifier>
            </dependency>
__pomgen.end_dependency_customization__
#{pomgen.crawled_external_dependencies}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>cg</groupId>
                <artifactId>ca</artifactId>
                <version>0.0.1</version>
                <classifier>sources</classifier>
                <scope>test</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep, pom_template)
        crawled_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_all_dependencies(set(), set([crawled_dep]), ())

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template_unknown_variable(self):
        """
        Verifies that an unknown variable in a pom template is handled and
        results in an error during template processing.
        """
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.maven_artifact("groupId", "artifactId",
                                               "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep,template_content = """
            my pom template with a bad ref #{bad1} and also #{bad2}""")

        with self.assertRaises(Exception) as ctx:
            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("bad1", str(ctx.exception))
        self.assertIn("bad2", str(ctx.exception))

    def test_depman_pom__sanity(self):
        """
        Ensures that dependency management pom generation isn't totally broken.
        """
        ws = workspace.Workspace("some/path", "", [], exclusions.src_exclusions())
        artifact_def = buildpom.MavenArtifactDef(
            "g1", "a2", "1.2.3", gen_dependency_management_pom=True)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DependencyManagementPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)
        guava = dependency.new_dep_from_maven_art_str("google:guava:1", "guav")
        force = dependency.new_dep_from_maven_art_str("force:commons:1", "forc")

        pomgen.register_all_dependencies(set(), set(), (guava, force,))
        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)
        
        self.assertIn("<packaging>pom</packaging>", generated_pom)
        self.assertIn("<dependencyManagement>", generated_pom)
        self.assertIn("<artifactId>guava</artifactId>", generated_pom)
        self.assertIn("<artifactId>commons</artifactId>", generated_pom)


if __name__ == '__main__':
    unittest.main()
        

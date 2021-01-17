"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
from common import maveninstallinfo
from common import pomgenmode
from config import exclusions
from crawl import bazel
from crawl import buildpom
from crawl import dependency
from crawl import pom
from crawl import pomcontent
from crawl import workspace
import unittest


TEST_POM_TEMPLATE = """
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <groupId>#{group_id}</groupId>
    <artifactId>#{artifact_id}</artifactId>
    <version>#{version}</version>
    <packaging>jar</packaging>

#{dependencies}
</project>
"""


class PomTest(unittest.TestCase):

    def setUp(self):
        f = dependency.new_dep_from_maven_art_str
        all_excluded_dep = f("*:*:-1", "maven")
        t1_dep = f("gt1:t1:1.0.0", "maven")
        t2_dep = f("gt2:t2:1.0.0", "maven")
        e1_dep = f("ge1:e1:-1.0.0", "maven")
        self.orig_bazel_parse_maven_install = bazel.parse_maven_install
        query_result = [
            (f("com.google.guava:guava:23.0", "maven"), [t1_dep, t2_dep], [all_excluded_dep]),
            (f("org.apache.maven:maven-artifact:3.3.9", "maven"), [], []),
            (f("ch.qos.logback:logback-classic:1.2.3", "maven"), [], []),
            (f("aopalliance:aopalliance:jar:1.0.0", "maven"), [], [e1_dep]),
            (t2_dep, [], []),
        ]
        bazel.parse_maven_install = lambda name, path: query_result
    
    def tearDown(self):
        bazel.parse_maven_install = self.orig_bazel_parse_maven_install

    def test_dynamic_pom__sanity(self):
        """
        Ensures that dynamic pom generation isn't totally broken.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        artifact_def = buildpom._augment_art_def_values(artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)

        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: ("@maven//:com_google_guava_guava", "@maven//:aopalliance_aopalliance", "@maven//:ch_qos_logback_logback_classic", "@maven//:gt2_t2" )
            _, _, deps = pomgen.process_dependencies()
            pomgen.register_dependencies(deps)
            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

            self.assertIn("""<groupId>g1</groupId>
    <artifactId>a2</artifactId>
    <version>1.2.3</version>
    <packaging>jar</packaging>""", generated_pom)
            
            self.assertIn("""<groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>23.0</version>
            <exclusions>
                <exclusion>
                    <groupId>*</groupId>
                    <artifactId>*</artifactId>
                </exclusion>
            </exclusions>""", generated_pom)

            self.assertIn("""<groupId>aopalliance</groupId>
            <artifactId>aopalliance</artifactId>
            <version>1.0.0</version>
            <exclusions>
                <exclusion>
                    <groupId>ge1</groupId>
                    <artifactId>e1</artifactId>
                </exclusion>
            </exclusions>""", generated_pom)

            self.assertIn("""<dependency>
            <groupId>ch.qos.logback</groupId>
            <artifactId>logback-classic</artifactId>
            <version>1.2.3</version>
        </dependency>""", generated_pom)

            self.assertIn("""    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>gt1</groupId>
                <artifactId>t1</artifactId>
                <version>1.0.0</version>
            </dependency>""", generated_pom)

            # deps are BUILD file order
            aop_index = generated_pom.index("<artifactId>aopalliance</artifactId>")
            guava_index = generated_pom.index("<artifactId>guava</artifactId>")
            self.assertTrue(guava_index < aop_index)

            # gt2:t2 is a transitive to guava, but because it is also
            # referenced explicitly, it is excluded from <dependencyManagement>
            depman_index = generated_pom.index("<dependencyManagement>")
            t2_index = generated_pom.index("<artifactId>t2</artifactId>")
            self.assertTrue(t2_index < depman_index) # t2 is not managed
            self.assertEqual(1, generated_pom.count("<artifactId>t2</artifactId>"))
        finally:
            bazel.query_java_library_deps_attributes = org_function

    def test_dynamic_pom__gen_description(self):
        """
        Tests that the <description> element is correctly added, if requested.
        """
        exepcted_pom = """<project>
    <description>
        this is a cool description
    </description>

</project>
"""
        pc = pomcontent.PomContent()
        pc.description = "this is a cool description"
        ws = workspace.Workspace("some/path", [], 
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pc)
        pom_template = """<project>
#{description}
</project>
"""
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, pom_template)
        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)
        self.assertEqual(exepcted_pom, generated_pom)

    def test_dynamic_pom__remove_description_token_if_no_value(self):
        """
        Tests that the #{description} token is removed if no description value
        is provided.
        """
        exepcted_pom = """<project>
</project>
"""
        pc = pomcontent.PomContent()
        # pc.description IS NOT set here - that's the point of this test
        ws = workspace.Workspace("some/path", [],
                                 exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pc)
        pom_template = """<project>
#{description}
</project>
"""
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, pom_template)

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(exepcted_pom, generated_pom)

    def test_dyamic_pom__no_dep_management(self):
        """
        If there are not registered transitives, we don't generate
        a dependencyManagement section.
        """
        # we need to overwrite what the default setUp method did to remove all
        # transitives
        f = dependency.new_dep_from_maven_art_str
        query_result = [
            (f("com.google.guava:guava:23.0", "maven"), [], []),
        ]
        orig_bazel_parse_maven_install = bazel.parse_maven_install
        bazel.parse_maven_install = lambda name, path: query_result
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        artifact_def = buildpom._augment_art_def_values(artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)
        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: ("@maven//:com_google_guava_guava", )
            _, _, deps = pomgen.process_dependencies()
            pomgen.register_dependencies(deps)

            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

            self.assertIn("""<dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>23.0</version>""", generated_pom)
            self.assertNotIn("<dependencyManagement>", generated_pom)

        finally:
            bazel.query_java_library_deps_attributes = org_function

    def test_dynamic_pom__do_not_include_deps(self):
        """
        Tests the seldomly used "include_deps = False" BUILD.pom attribute.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("g1", "a2", "1.2.3")
        artifact_def = buildpom._augment_art_def_values(artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)

        pomgen = pom.DynamicPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)

        org_function = bazel.query_java_library_deps_attributes
        try:
            bazel.query_java_library_deps_attributes = lambda r, p: ("@maven//:com_google_guava_guava", "@maven//:aopalliance_aopalliance", )
            _, _, deps = pomgen.process_dependencies()
            pomgen.register_dependencies(deps)

            generated_pom = pomgen.gen(pom.PomContentType.GOLDFILE)

            self.assertIn("""<groupId>g1</groupId>
    <artifactId>a2</artifactId>
    <version>***</version>
    <packaging>jar</packaging>""", generated_pom)

            self.assertIn("""<groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>23.0</version>
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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.4.4")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = """
unqualified #{ch_qos_logback_logback_classic.version}
qualified #{@maven//:ch_qos_logback_logback_classic.version}
coord #{ch.qos.logback:logback-classic:version}
monorepo artifact version #{version}
"""
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("unqualified 1.2.3", generated_pom)
        self.assertIn("qualified 1.2.3", generated_pom)
        self.assertIn("monorepo artifact version 1.4.4", generated_pom)

    def test_template_var_sub__monorepo_deps(self):
        """
        Verifies references to monorepo versions in a pom template.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.MavenArtifactDef("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = "srpc #{com.grail.srpc:srpc-api:version}"
        srpc_artifact_def = buildpom.MavenArtifactDef(
            "com.grail.srpc", "srpc-api", "5.6.7", bazel_package="a/b/c")
        srpc_dep = dependency.MonorepoDependency(srpc_artifact_def, bazel_target=None)
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        pomgen.register_dependencies_transitive_closure__library(set([srpc_dep]))

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)
        
        self.assertIn("srpc 5.6.7", generated_pom)

    def test_template_var_sub__conflicting_gav__ext_and_BUILDpom(self):
        """
        Verifies error handling when gavs are conflicting between external deps
        and what is set in BUILD.pom files.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = "srpc #{g:a:version}"
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        art = buildpom.MavenArtifactDef("com.google.guava","guava","26.0", bazel_package="a/b/c")
        d = dependency.MonorepoDependency(art, bazel_target=None)
        pomgen.register_dependencies_transitive_closure__library(set([d]))

        with self.assertRaises(Exception) as ctx:
            pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("Found multiple artifacts with the same groupId:artifactId", str(ctx.exception))
        self.assertIn("com.google.guava:guava", str(ctx.exception))

    def test_template_genmode__goldfile(self):
        """
        Verifies version omissions when genmode is GOLDFILE.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 self._mocked_mvn_install_info("maven"),
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        srpc_artifact_def = buildpom.maven_artifact("com.grail.srpc",
                                                    "srpc-api", "5.6.7")
        srpc_artifact_def = buildpom._augment_art_def_values(srpc_artifact_def, None, "pack1", None, None, pomgenmode.DYNAMIC)
        srpc_dep = dependency.MonorepoDependency(srpc_artifact_def, bazel_target=None)
        artifact_def.custom_pom_template_content = """
this artifact version #{version}
logback coord #{ch.qos.logback:logback-classic:version}
logback qualified #{@maven//:ch_qos_logback_logback_classic.version}
logback unqualified #{ch_qos_logback_logback_classic.version}
srpc #{com.grail.srpc:srpc-api:version}
"""
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        pomgen.register_dependencies_transitive_closure__library(set([srpc_dep]))
        generated_pom = pomgen.gen(pomcontenttype=pom.PomContentType.GOLDFILE)

        self.assertIn("this artifact version ***", generated_pom)
        self.assertIn("logback coord 1.2.3", generated_pom)
        self.assertIn("logback qualified 1.2.3", generated_pom)
        self.assertIn("logback unqualified 1.2.3", generated_pom)
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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = pom_template
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)

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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = pom_template
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template__library_transitives(self):
        """
        Verifies that transitive dependencies can be referenced using the
        property pomgen.transitive_closure_of_library_dependencies.
        """
        pom_template = """
<project>
    <dependencyManagement>
        <dependencies>
#{pomgen.transitive_closure_of_library_dependencies}
        </dependencies>
    </dependencyManagement>
</project>
"""

        expected_pom = """
<project>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>com.grail.srpc</groupId>
                <artifactId>srpc-api</artifactId>
                <version>5.6.7</version>
            </dependency>
            <dependency>
                <groupId>cg</groupId>
                <artifactId>ca</artifactId>
                <version>0.0.1</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
"""
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = pom_template
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        srpc_artifact_def = buildpom.MavenArtifactDef(
            "com.grail.srpc", "srpc-api", "5.6.7", bazel_package="a/b/c")
        internal_dep = dependency.MonorepoDependency(srpc_artifact_def, bazel_target=None)

        external_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_dependencies_transitive_closure__library(set([external_dep, internal_dep]))

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
#{pomgen.transitive_closure_of_library_dependencies}
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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = pom_template
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        crawled_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_dependencies_transitive_closure__library(set([crawled_dep]))

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
#{pomgen.transitive_closure_of_library_dependencies}
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
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId", "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = pom_template
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)
        crawled_dep = dependency.ThirdPartyDependency("name", "cg", "ca", "0.0.1")
        pomgen.register_dependencies_transitive_closure__library(set([crawled_dep]))

        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertEqual(expected_pom, generated_pom)

    def test_template_unknown_variable(self):
        """
        Verifies that an unknown variable in a pom template is handled and
        results in an error during template processing.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.maven_artifact("groupId", "artifactId",
                                               "1.2.3")
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        artifact_def.custom_pom_template_content = "my pom template with a bad ref #{bad1} and also #{bad2}"
        pomgen = pom.TemplatePomGen(ws, artifact_def, dep)

        with self.assertRaises(Exception) as ctx:
            generated_pom = pomgen.gen(pom.PomContentType.RELEASE)

        self.assertIn("bad1", str(ctx.exception))
        self.assertIn("bad2", str(ctx.exception))

    def test_depman_pom__sanity(self):
        """
        Ensures that dependency management pom generation isn't totally broken.
        """
        ws = workspace.Workspace("some/path", [], exclusions.src_exclusions(),
                                 maveninstallinfo.NOOP,
                                 pomcontent.NOOP)
        artifact_def = buildpom.MavenArtifactDef(
            "g1", "a2", "1.2.3", gen_dependency_management_pom=True)
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        pomgen = pom.DependencyManagementPomGen(ws, artifact_def, dep, TEST_POM_TEMPLATE)
        guava = dependency.new_dep_from_maven_art_str("google:guava:1", "guav")
        force = dependency.new_dep_from_maven_art_str("force:commons:1", "forc")

        pomgen.register_dependencies_transitive_closure__artifact((guava, force,))
        generated_pom = pomgen.gen(pom.PomContentType.RELEASE)
        
        self.assertIn("<packaging>pom</packaging>", generated_pom)
        self.assertIn("<dependencyManagement>", generated_pom)
        self.assertIn("<artifactId>guava</artifactId>", generated_pom)
        self.assertIn("<artifactId>commons</artifactId>", generated_pom)

    def _mocked_mvn_install_info(self, maven_install_name):
        mii = maveninstallinfo.MavenInstallInfo(())
        mii.get_maven_install_names_and_paths = lambda r: [(maven_install_name, "some/repo/path",)]
        return mii


if __name__ == '__main__':
    unittest.main()
        

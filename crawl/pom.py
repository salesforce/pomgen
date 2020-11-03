"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module contains pom.xml generation logic.
"""

from common import pomgenmode
import copy
from crawl import bazel
from crawl import pomparser
from crawl import workspace
import os
import re


class PomContentType:
    """
    Available pom content types:
      
      RELEASE - this is the default, standard pom.xml, based on BUILD file or
          pom.template content.

      GOLDFILE - this pom content is meant for comparing against another
                 previously generated pom (the "goldfile" pom). This content
                 type differs from the default RELEASE type in the following 
                 ways:
                   - dependencies are explictly ordered (default is BUILD order)
                   - versions of monorepo-based dependencies are removed
    """
    RELEASE = 0
    GOLDFILE = 1

    MASKED_VERSION = "***"


def get_pom_generator(workspace, pom_template, artifact_def, dependency):
    """
    Returns a pom.xml generator (AbstractPomGen implementation) for the
    specified artifact_def.

    Arguments:
        workspace: the crawl.workspace.Workspace singleton
        pom_template: the template to use for generating dynamic (jar) pom.xmls
        artifact_def: the crawl.buildpom.MavenArtifactDef instance for access 
            to the parsed MVN-INF/* metadata files
        dependency: the dependency pointing to this artifact_def
    """
    assert artifact_def is not None
    assert dependency is not None

    mode = artifact_def.pom_generation_mode
    if mode is pomgenmode.DYNAMIC:
        also_generate_dep_man_pom = artifact_def.gen_dependency_management_pom
        if also_generate_dep_man_pom:
            return PomWithCompanionDependencyManagementPomGen(
                workspace, artifact_def, dependency, pom_template)
        else:
            return DynamicPomGen(
                workspace, artifact_def, dependency, pom_template)
    elif mode is pomgenmode.TEMPLATE:
        return TemplatePomGen(workspace, artifact_def, dependency)
    elif mode is pomgenmode.SKIP:
        return NoopPomGen(workspace, artifact_def, dependency)
    else:
        raise Exception("Bug: unknown pom_generation_mode [%s] for %s" % (mode, artifact_def.bazel_package))


class AbstractPomGen(object):

    def __init__(self, workspace, artifact_def, dependency):
        self._artifact_def = artifact_def
        self._dependency = dependency
        self._workspace = workspace

    @property
    def artifact_def(self):
        return self._artifact_def

    @property
    def bazel_package(self):
        return self._artifact_def.bazel_package

    @property 
    def dependency(self):
        return self._dependency

    def process_dependencies(self):
        """
        Discovers the dependencies of this artifact (bazel target).

        This method *must* be called before requesting this instance to generate
        a pom.

        This method returns a tuple of 3 (!) lists of Dependency instances: 
            (l1, l2, l3)
            l1: all source dependencies (== references to other bazel packages)
            l2: all external dependencies (maven jars)
            l3: l1 and l2 together, in "discovery order"

        This method is not meant to be overwritten by subclasses.
        """
        all_deps = ()
        if self._artifact_def.deps is not None:
            all_deps = self._workspace.parse_dep_labels(self._artifact_def.deps)
        all_deps += self._load_additional_dependencies_hook()

        source_dependencies = []
        ext_dependencies = []
        for dep in all_deps:
            if dep.bazel_package is None:
                ext_dependencies.append(dep)
            else:
                source_dependencies.append(dep)
        
        return (tuple(source_dependencies), 
                tuple(ext_dependencies), 
                tuple(all_deps))

    def register_dependencies(self, dependencies):
        """
        Sets the dependencies to use for pom generation.

        This method is called after bazel packages have been processed, with
        the final list of dependencies to include in the generated pom.

        This method *must* be called before requesting this instance to generate
        a pom.

        Subclasses may implement.
        """
        pass

    def register_all_dependencies(self, crawled_bazel_packages,
                                  crawled_external_dependencies,
                                  transitive_closure_dependencies):
        """
        This method is called after all bazel packages have been crawled and
        processed, with the following sets of Dependency instances:

            - crawled_bazel_packages: 
                  the set of ALL crawled bazel packages
            - crawled_external_dependencies: 
                  the set of ALL crawled (discovered) external dependencies
            - transitive_closure_dependencies
                  for this pom, all its dependencies AND all the dependencies
                  of its dependencies, all the way down.

        Subclasses may implement.
        """
        pass

    def gen(self, pomcontenttype):
        """
        Returns the generated pom.xml as a string.  This method may be called
        multiple times, and must therefore be idempotent.

        Subclasses must implement.
        """
        raise Exception("must be implemented by subclass")

    def get_companion_generators(self):
        """
        Returns an iterable of companion generators. These poms are not used
        as inputs to any pomgen algorithm.  They are only part of the final
        outputs.

        Subclasses may implement.
        """
        return ()

    def _load_additional_dependencies_hook(self):
        """
        Returns a list of dependency instances referenced by the current 
        package.

        Only meant to be overridden by subclasses.
        """
        return ()

    def _artifact_def_version(self, pomcontenttype):
        """
        Returns the associated artifact's version, based on the specified 
        PomContentType.

        This method is only intended to be called by subclasses.
        """
        return PomContentType.MASKED_VERSION if pomcontenttype is PomContentType.GOLDFILE else self._artifact_def.version

    def _dep_version(self, pomcontenttype, dep):
        """
        Returns the given dependency's version, based on the specified
        PomContentType.

        This method is only intended to be called by subclasses.
        """
        return PomContentType.MASKED_VERSION if pomcontenttype is PomContentType.GOLDFILE and dep.bazel_package is not None else dep.version

    def _xml(self, content, element, indent, value=None, close_element=False):
        """
        Helper method used to generated xml.

        This method is only intended to be called by subclasses.
        """
        if value is None:
            if close_element:
                return "%s%s</%s>%s" % (content, ' '*(indent - _INDENT), element, os.linesep), indent - _INDENT
            else:
                return "%s%s<%s>%s" % (content, ' '*indent, element, os.linesep), indent + _INDENT
        else:
            return "%s%s<%s>%s</%s>%s" % (content, ' '*indent, element, value, element, os.linesep), indent

    def _gen_dependency_element(self, pomcontenttype, dep, content, indent, close_element):
        """
        Generates a pomx.xml <dependency> element.

        Returns the generated content and the current identation level as a 
        tuple: (content, indent)

        This method is only intended to be called by subclasses.
        """
        content, indent = self._xml(content, "dependency", indent)
        content, indent = self._xml(content, "groupId", indent, dep.group_id)
        content, indent = self._xml(content, "artifactId", indent, dep.artifact_id)
        content, indent = self._xml(content, "version", indent, self._dep_version(pomcontenttype, dep))
        if dep.classifier is not None:
            content, indent = self._xml(content, "classifier", indent, dep.classifier)
        if dep.scope is not None:
            content, indent = self._xml(content, "scope", indent, dep.scope)
        if close_element:
            content, indent = self._xml(content, "dependency", indent, close_element=True)
        return content, indent

    def _gen_exclusions(self, content, indent, group_and_artifact_ids):
        """
        This method is only intended to be called by subclasses.
        """
        content, indent = self._xml(content, "exclusions", indent)
        for ga in group_and_artifact_ids:
            content, indent = self._xml(content, "exclusion", indent)
            content, indent = self._xml(content, "groupId", indent, ga[0])
            content, indent = self._xml(content, "artifactId", indent, ga[1])
            content, indent = self._xml(content, "exclusion", indent, close_element=True)
        content, indent = self._xml(content, "exclusions", indent, close_element=True)
        return content, indent

    def _remove_token(self, content, token_name):
        """
        This method is only intended to be called by subclasses.
        """
        # assumes token is on one line by itself
        i = content.find(token_name)
        if i == -1:
            return content
        else:
            j = content.find(os.linesep, i)
            if j == -1:
                j = len(content) - 1
            return content[:i] + content[j+len(os.linesep):]

    def _gen_description(self, description):
        content = ""
        content, indent = self._xml(content, "description", indent=_INDENT)
        content = "%s%s%s%s" % (content, ' '*indent, description, os.linesep)
        content, indent = self._xml(content, "description", indent=indent, close_element=True)
        return content

    def _handle_description(self, content, description):
        if description is None:
            return self._remove_token(content, "#{description}")
        else:
            return content.replace("#{description}", self._gen_description(description))

class NoopPomGen(AbstractPomGen):
    """
    A placeholder pom generator that doesn't generator anything, but still
    follows references.
    """
    def __init__(self, workspace, artifact_def, dependency):
        super(NoopPomGen, self).__init__(workspace, artifact_def, dependency)

    def _load_additional_dependencies_hook(self):
        return _query_dependencies(self._workspace, self._artifact_def, 
                                   self._dependency)


class TemplatePomGen(AbstractPomGen):

    BAZEL_PGK_DEPS_PROP_NAME = "pomgen.crawled_bazel_packages"
    EXT_DEPS_PROP_NAME = "pomgen.crawled_external_dependencies"
    UNUSED_CONFIGURED_DEPS_PROP_NAME = "pomgen.unencountered_dependencies"
    DEPS_CONFIG_SECTION_START = "__pomgen.start_dependency_customization__"
    DEPS_CONFIG_SECTION_END = "__pomgen.end_dependency_customization__"

    # these properties need to be replaced first in pom templates
    # because their values may reference other properties
    INITAL_PROPERTY_SUBSTITUTIONS = (EXT_DEPS_PROP_NAME, 
                                     BAZEL_PGK_DEPS_PROP_NAME, 
                                     UNUSED_CONFIGURED_DEPS_PROP_NAME,)

    """
    Generates a pom.xml based on a template file.
    """
    def __init__(self, workspace, artifact_def, dependency):
        super(TemplatePomGen, self).__init__(workspace, artifact_def, dependency)
        self.crawled_bazel_packages = set()
        self.crawled_external_dependencies = set()

    def register_all_dependencies(self,
                                  crawled_bazel_packages,
                                  crawled_external_dependencies,
                                  transitive_closure_dependencies):
        self.crawled_bazel_packages = crawled_bazel_packages
        self.crawled_external_dependencies = crawled_external_dependencies

    def gen(self, pomcontenttype):
        pom_content, parsed_dependencies = self._process_pom_template_content(self.artifact_def.custom_pom_template_content)

        properties = self._get_properties(pomcontenttype, parsed_dependencies)

        for k in TemplatePomGen.INITAL_PROPERTY_SUBSTITUTIONS:
            if k in properties:
                pom_content = pom_content.replace("#{%s}" % k, properties[k])
                del properties[k]

        for k in properties.keys():
            pom_content = pom_content.replace("#{%s}" % k, properties[k])

        bad_refs = [match.group(1) for match in re.finditer(r"""\#\{(.*?)\}""", pom_content) if len(match.groups()) == 1]
        if len(bad_refs) > 0:
            raise Exception("pom template for [%s] has unresolvable references: %s" % (self._artifact_def, bad_refs))
        return pom_content

    def _process_pom_template_content(self, pom_template_content):
        """
        Handles the special "dependency config markers" that may be present
        in the pom template file.

        Returns a tuple:
           (updated_pom_template_content, pomparser.ParsedDependencies instance)
        """
        start_section_index = pom_template_content.find(TemplatePomGen.DEPS_CONFIG_SECTION_START)
        if start_section_index == -1:
            return pom_template_content, pomparser.ParsedDependencies()
        else:
            end_section_index = pom_template_content.index(TemplatePomGen.DEPS_CONFIG_SECTION_END)
            dynamic_deps_content = pom_template_content[start_section_index + len(TemplatePomGen.DEPS_CONFIG_SECTION_START):end_section_index]
            # make this a well formed pom
            dynamic_deps_content = "<project><dependencies>%s</dependencies></project>" % dynamic_deps_content
            parsed_dependencies = pomparser.parse_dependencies(dynamic_deps_content)
            # now that dependencies have been parsed, remove the special 
            # depdendency config section from pom template
            pom_template_content = pom_template_content[:start_section_index] + pom_template_content[end_section_index + len(TemplatePomGen.DEPS_CONFIG_SECTION_END)+1:]
            return (pom_template_content, parsed_dependencies)

    def _get_properties(self, pomcontenttype, pom_template_parsed_deps):
        properties = self._get_version_properties(pomcontenttype)
        properties.update(self._get_crawled_dependencies_properties(pomcontenttype, pom_template_parsed_deps))            
        return properties

    def _get_version_properties(self, pomcontenttype):
        # the version of all dependencies can be referenced in a pom template
        # using the syntax: #{<groupId>:<artifactId>:[<classifier>:]version}.
        #
        # Additionally, versions of external dependencies may be referenced
        # using the dependency's "maven_jar" name, for example:
        # #{com_google_guava_guava.version}
        # 
        # the latter form is being phased out to avoid having to change pom
        # templates when dependencies move in (and out?) of the monorepo.

        #{<groupId>:<artifactId>:[<classifier>:]version} -> version value
        #{com_google_guava_guava.version} -> version value
        key_to_version = {}

        # internal bookeeping for this method
        key_to_dep = {}

        all_deps = \
            list(self._workspace.name_to_external_dependencies.values()) + \
            list(self.crawled_bazel_packages)

        for dep in all_deps:
            key = "%s:version" % dep.maven_coordinates_name
            if key in key_to_version:
                found_conflicting_deps = True
                conflicting_dep = key_to_dep[key]
                if dep.bazel_package is None and conflicting_dep.bazel_package is None:
                    # both deps are external (Nexus) deps, this is weird, but
                    # ok, as long as their versions are identical, so check for
                    # that
                    if dep.version == conflicting_dep.version:
                        found_conflicting_deps = False # ok

                if found_conflicting_deps:
                    msg = "Found multiple artifacts with the same groupId:artifactId: \"%s\". This means that there are multiple BUILD.pom files defining the same artifact, or that a BUILD.pom defined artifact has the same groupId and artifactId as a referenced maven_jar, or that multiple maven_jars reference the same groupId/artifactId but different versions" % dep.maven_coordinates_name
                    raise Exception(msg)
            key_to_version[key] = self._dep_version(pomcontenttype, dep)
            key_to_dep[key] = dep
            if dep.bazel_label_name is not None:
                key = "%s.version" % dep.bazel_label_name
                assert key not in key_to_version
                key_to_version[key] = dep.version
                key_to_dep[key] = dep

        # the maven coordinates of this artifact can be referenced directly:
        key_to_version["artifact_id"] = self._artifact_def.artifact_id
        key_to_version["group_id"] = self._artifact_def.group_id
        key_to_version["version"] = self._artifact_def_version(pomcontenttype)

        return key_to_version

    def _get_crawled_dependencies_properties(self, pomcontenttype, pom_template_parsed_deps):
        # this is somewhat lame: an educated guess on where the properties
        # being build here will be referenced (within 
        # project/depedencyManagement/dependencies)
        indent = _INDENT*3

        properties = {}

        content = self._build_deps_property_content(self.crawled_bazel_packages,
                                                    pom_template_parsed_deps, 
                                                    pomcontenttype, indent)
        properties[TemplatePomGen.BAZEL_PGK_DEPS_PROP_NAME] = content

        content = self._build_deps_property_content(self.crawled_external_dependencies,
                                                    pom_template_parsed_deps, 
                                                    pomcontenttype, indent)
        properties[TemplatePomGen.EXT_DEPS_PROP_NAME] = content

        pom_template_only_deps = pom_template_parsed_deps.get_parsed_deps_set_missing_from(self.crawled_bazel_packages, self.crawled_external_dependencies)
        content = self._build_template_only_deps_property_content(\
            _sort(pom_template_only_deps),
            pom_template_parsed_deps,
            indent)
        properties[TemplatePomGen.UNUSED_CONFIGURED_DEPS_PROP_NAME] = content

        return properties

    def _build_template_only_deps_property_content(self, deps,
                                                   pom_template_parsed_deps,
                                                   indent):
        content = ""
        for dep in deps:
            raw_xml = pom_template_parsed_deps.get_parsed_xml_str_for(dep)
            content += pomparser.indent_xml(raw_xml, indent)
        content = content.rstrip()
        return content

    def _build_deps_property_content(self, deps, pom_template_parsed_deps, 
                                     pomcontenttype, indent):

        content = ""
        deps = _sort(deps)
        for dep in deps:
            dep = self._copy_attributes_from_parsed_dep(dep, pom_template_parsed_deps)
            pom_template_exclusions = pom_template_parsed_deps.get_parsed_exclusions_for(dep)
            dep_has_exclusions = len(pom_template_exclusions) > 0
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=not dep_has_exclusions)
            if dep_has_exclusions:
                exclusions = list(pom_template_exclusions)
                exclusions.sort()
                group_and_artifact_ids = [(d.group_id, d.artifact_id) for d in exclusions]
                content, indent = self._gen_exclusions(content, indent, group_and_artifact_ids)
                content, indent = self._xml(content, "dependency", indent, close_element=True)         

        content = content.rstrip()
        return content

    def _copy_attributes_from_parsed_dep(self, dep, pom_template_parsed_deps):
        # check attributes of parsed deps in the pom template
        # we support "classifier" and "scope"
        parsed_dep = pom_template_parsed_deps.get_parsed_dependency_for(dep)
        if parsed_dep is not None:
            if (parsed_dep.scope is not None or
                parsed_dep.classifier is not None):
                dep = copy.copy(dep)
                if parsed_dep.scope is not None:
                    dep.scope = parsed_dep.scope
                if parsed_dep.classifier is not None:
                    dep.classifier = parsed_dep.classifier
        return dep


class DynamicPomGen(AbstractPomGen):
    """
    A non-generic, non-reusable, specialized pom.xml generator, targeted 
    for the "monorepo pom generation" use-case.

    Generates a pom.xm file based on the specified singleton (shared) template.

    The following placesholders must exist in the specified template:
       #{dependencies} - will be replaced with the <dependencies> section

    The following placesholders may exist in the specified template:

       #{artifact_id}
       #{group_id}
       #{version}
    """
    def __init__(self, workspace, artifact_def, dependency, pom_template):
        super(DynamicPomGen, self).__init__(workspace, artifact_def, dependency)
        self.pom_content = workspace.pom_content
        self.pom_template = pom_template
        self.dependencies = ()

    def register_dependencies(self, dependencies):
        self.dependencies = dependencies

    def gen(self, pomcontenttype):
        content = self.pom_template.replace("#{group_id}", self._artifact_def.group_id)
        content = content.replace("#{artifact_id}", self._artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("#{version}", version)
        content = self._handle_description(content, self.pom_content.description)
        if len(self.dependencies) == 0:
            content = self._remove_token(content, "#{dependencies}")
        else:
            content = content.replace("#{dependencies}", self._gen_dependencies(pomcontenttype))
        return content

    def _load_additional_dependencies_hook(self):
        return _query_dependencies(self._workspace, self._artifact_def,
                                   self._dependency)

    def _gen_dependencies(self, pomcontenttype):
        deps = self.dependencies
        if pomcontenttype == PomContentType.GOLDFILE:
            deps = list(deps)
            deps.sort()

        content = ""
        content, indent = self._xml(content, "dependencies", indent=_INDENT)
        for dep in deps:
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=False)
            if dep.bazel_package is None:
                # for 3rd party deps that do not live in the monorepo, add
                # exclusions to mimic how dependencies are handled in BUILD
                # files
                excluded_group_and_artifact_ids = [("*", "*")]
                excluded_group_and_artifact_ids += self._get_explicit_exclusions_for_dep(dep)
                content, indent = self._gen_exclusions(content, indent, excluded_group_and_artifact_ids)

            content, indent = self._xml(content, "dependency", indent, close_element=True)
        content, indent = self._xml(content, "dependencies", indent, close_element=True)
        return content

    def _get_explicit_exclusions_for_dep(self, dep):
        """
        A few jar artifacts reference dependencies that do not exist; these 
        need to be excluded explicitly.

        Returns tuples (group_id, artifact_id) to exclude.
        """
        if dep.group_id == "com.twitter.common.zookeeper" and \
           dep.artifact_id in ("client", "group", "server-set"):
            return (("com.twitter", "finagle-core-java"),
                    ("com.twitter", "util-core-java"),
                    ("org.apache.zookeeper", "zookeeper-client"))

        return ()


class DependencyManagementPomGen(AbstractPomGen):
    """
    Generates a dependency management" only pom, containing a
    <dependencyManagement> section with the transitive closure of all
    dependencies of the backing artifact.

    The following placesholders must exist in the specified template:
       #{dependencies} - will be replaced with the <dependencyManagement>
                         section

    The following placesholders may exist in the specified template:

       #{artifact_id}
       #{group_id}
       #{version}
    """
    def __init__(self, workspace, artifact_def, dependency, pom_template):
        super(DependencyManagementPomGen, self).__init__(workspace, artifact_def, dependency)
        self.pom_template = pom_template
        self.pom_content = workspace.pom_content
        self.transitive_closure_dependencies = ()

    def register_all_dependencies(self, crawled_bazel_packages,
                                  crawled_external_dependencies,
                                  transitive_closure_dependencies):
        self.transitive_closure_dependencies = transitive_closure_dependencies

    def gen(self, pomcontenttype):
        assert pomcontenttype == PomContentType.RELEASE
        content = self.pom_template.replace("#{group_id}", self._artifact_def.group_id)
        # by convention, we add the suffix ".depmanagement" to the artifactId
        # so com.blah is the real jar artifact and com.blah.depmanagement
        # is the dependency management pom for that artficat
        content = content.replace("#{artifact_id}", "%s.depmanagement" % self._artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("#{version}", version)
        content = self._handle_description(content, self.pom_content.description)
        if len(self.transitive_closure_dependencies) == 0:
            content = self._remove_token(content, "#{dependencies}")
        else:
            content = content.replace("#{dependencies}", self._gen_dependency_management())

        # we assume the template specified <packaging>jar</packaging>
        # there room for improvement here for sure
        expected_packaging = "<packaging>jar</packaging>"
        if not expected_packaging in content:
            raise Exception("The pom template must have %s" % expected_packaging)
        content = content.replace(expected_packaging, expected_packaging.replace("jar", "pom"))
        
        return content

    def _gen_dependency_management(self):
        deps = self.transitive_closure_dependencies
        content = ""
        content, indent = self._xml(content, "dependencyManagement", indent=_INDENT)
        content, indent = self._xml(content, "dependencies", indent)
        for dep in deps:
            content, indent = self._gen_dependency_element(PomContentType.RELEASE, dep, content, indent, close_element=True)
        content, indent = self._xml(content, "dependencies", indent, close_element=True)
        content, indent = self._xml(content, "dependencyManagement", indent, close_element=True)
        return content


class PomWithCompanionDependencyManagementPomGen(AbstractPomGen):
    """
    Composite PomGen implementation with a companion PomGen the generates a
    DependencyManagement pom.
    """
    def __init__(self, workspace, artifact_def, dependency, pom_template):
        super(PomWithCompanionDependencyManagementPomGen, self).__init__(workspace, artifact_def, dependency)
        self.pomgen = DynamicPomGen(workspace, artifact_def, dependency, pom_template)
        self.depmanpomgen = DependencyManagementPomGen(workspace, artifact_def, dependency, pom_template)

    def register_dependencies(self, dependencies):
        self.pomgen.register_dependencies(dependencies)
        self.depmanpomgen.register_dependencies(dependencies)

    def register_all_dependencies(self, crawled_bazel_packages,
                                  crawled_external_dependencies,
                                  transitive_closure_dependencies):
        self.pomgen.register_all_dependencies(crawled_bazel_packages,
                                              crawled_external_dependencies,
                                              transitive_closure_dependencies)
        self.depmanpomgen.register_all_dependencies(crawled_bazel_packages,
                                                    crawled_external_dependencies,
                                                    transitive_closure_dependencies)

    def gen(self, pomcontenttype):
        return self.pomgen.gen(pomcontenttype)

    def get_companion_generators(self):
        return (self.depmanpomgen,)

    def _load_additional_dependencies_hook(self):
        return self.pomgen._load_additional_dependencies_hook()


_INDENT = pomparser.INDENT


def _sort(s):
    """
    Converts the specified set to a list, and returns the list, sorted.
    """
    assert isinstance(s, set), "Expected a set"
    l = list(s)
    l.sort()
    return l


# this method delegates to bazel query to get the value of a bazel target's 
# "deps" and "runtime_deps" attributes. it really doesn't below in this module,
# because it has nothing to do with generating a pom.xml file.
# it could move into common.pomgenmode or live closer to the crawler
def _query_dependencies(workspace, artifact_def, dependency):
    if not artifact_def.include_deps:
        return ()
    else:
        try:
            label = _build_bazel_label(artifact_def.bazel_package,
                                       dependency.bazel_target)
            dep_labels = bazel.query_java_library_deps_attributes(
                workspace.repo_root_path, label)
            deps = workspace.parse_dep_labels(dep_labels)
            return workspace.normalize_deps(artifact_def, deps)
        except Exception as e:
            msg = e.message if hasattr(e, "message") else type(e)
            raise Exception("Error while processing dependencies: %s %s caused by %s" % (msg, artifact_def, repr(e)))


def _build_bazel_label(package, target):
    assert package is not None, "package should not be None"
    assert target is not None, "target should not be None"
    assert len(target) > 0, "target should not be an empty string for package [%s]" % package
    return "%s:%s" % (package, target)

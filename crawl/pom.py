"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module contains pom.xml generation logic.
"""

from common import pomgenmode
from common import logger
from common import common
import copy
from crawl import bazel
from crawl import pomparser
from crawl import workspace
from crawl import pomproperties
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

        self.dependencies = set()
        self.dependencies_artifact_transitive_closure = set()
        self.dependencies_library_transitive_closure = set()

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
        Registers the dependencies the backing artifact references explicitly.

        """
        self.dependencies = dependencies

    def register_dependencies_transitive_closure__artifact(self, dependencies):
        """
        Registers the transitive closure of dependencies for the artifact
        (target) backing this pom generator.
        """
        self.dependencies_artifact_transitive_closure = dependencies

    def register_dependencies_transitive_closure__library(self, dependencies):
        """
        Registers the transitive closure of dependencies for the library
        that the artifact backing this pom generator belongs to.
        """
        self.dependencies_library_transitive_closure = dependencies

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

    def _gen_dependency_element(self, pomcontenttype, dep, content, indent, close_element, group_version_dict={}):
        """
        Generates a pomx.xml <dependency> element.

        Returns the generated content and the current identation level as a 
        tuple: (content, indent)

        This method is only intended to be called by subclasses.
        """
        content, indent = common.xml(content, "dependency", indent)
        content, indent = common.xml(content, "groupId", indent, dep.group_id)
        content, indent = common.xml(content, "artifactId", indent, dep.artifact_id)
        version_from_dep = self._dep_version(pomcontenttype, dep)
        if dep.group_id in group_version_dict and version_from_dep == group_version_dict[dep.group_id].get_property_value():
            content, indent = common.xml(content, "version", indent, "${%s}" % group_version_dict[dep.group_id].get_property_name())
        else:
            content, indent = common.xml(content, "version", indent, version_from_dep)
        if dep.classifier is not None:
            content, indent = common.xml(content, "classifier", indent, dep.classifier)
        if dep.scope is not None:
            content, indent = common.xml(content, "scope", indent, dep.scope)
        if close_element:
            content, indent = common.xml(content, "dependency", indent, close_element=True)
        return content, indent

    def _gen_exclusions(self, content, indent, group_and_artifact_ids):
        """
        This method is only intended to be called by subclasses.
        """
        content, indent = common.xml(content, "exclusions", indent)
        for ga in group_and_artifact_ids:
            content, indent = common.xml(content, "exclusion", indent)
            content, indent = common.xml(content, "groupId", indent, ga[0])
            content, indent = common.xml(content, "artifactId", indent, ga[1])
            content, indent = common.xml(content, "exclusion", indent, close_element=True)
        content, indent = common.xml(content, "exclusions", indent, close_element=True)
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
        content, indent = common.xml(content, "description", indent=_INDENT)
        content = "%s%s%s%s" % (content, ' '*indent, description, os.linesep)
        content, indent = common.xml(content, "description", indent=indent, close_element=True)
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

    TRANSITIVE_DEPS_PROP_NAME = "pomgen.transitive_closure_of_library_dependencies"
    UNUSED_CONFIGURED_DEPS_PROP_NAME = "pomgen.unencountered_dependencies"
    DEPS_CONFIG_SECTION_START = "__pomgen.start_dependency_customization__"
    DEPS_CONFIG_SECTION_END = "__pomgen.end_dependency_customization__"
    PROPERTIES_SECTION_START = "<properties>"
    PROPERTIES_SECTION_END = "</properties>"

    # these properties need to be replaced first in pom templates
    # because their values may reference other properties
    INITAL_PROPERTY_SUBSTITUTIONS = (TRANSITIVE_DEPS_PROP_NAME,
                                     UNUSED_CONFIGURED_DEPS_PROP_NAME,)

    """
    Generates a pom.xml based on a template file.
    """
    def __init__(self, workspace, artifact_def, dependency):
        super(TemplatePomGen, self).__init__(workspace, artifact_def, dependency)
    def gen(self, pomcontenttype):
        pom_content = self.artifact_def.custom_pom_template_content
        pom_content, parsed_dependencies, parsed_properties = self._process_pom_template_content(pom_content)
        all_version_properties, template_version_properties, group_version_dict = self._get_version_properties(pomcontenttype, parsed_properties)
        for k in all_version_properties.keys():
            pom_content = pom_content.replace("#{%s}" % k, all_version_properties[k])
        generate_properties_section = "#{pomgen.generate_properties}"
        properties_section_start_index = pom_content.find(TemplatePomGen.PROPERTIES_SECTION_START)
        substitute_version_properties = False
        if generate_properties_section in pom_content or properties_section_start_index != -1:
            substitute_version_properties = True
        initial_properties, updated_group_version_dict = self._get_crawled_dependencies_properties(pomcontenttype, parsed_dependencies, group_version_dict, substitute_version_properties)
        version_properties_content = pomproperties.gen_version_properties(updated_group_version_dict, pom_content)

        if generate_properties_section in pom_content:
            content = ""
            content, indent = common.xml(content, "properties", indent=_INDENT)
            content += version_properties_content
            content, indent = common.xml(content, "properties", indent, close_element=True)
            pom_content = pom_content.replace(generate_properties_section, content)
        elif properties_section_start_index != -1:
            properties_section_end_index = pom_content.index(TemplatePomGen.PROPERTIES_SECTION_END)
            inject_index = pom_content[:properties_section_end_index].rfind(os.linesep) + 1
            pom_content = pom_content[:inject_index] + version_properties_content + pom_content[inject_index:]

        for k in TemplatePomGen.INITAL_PROPERTY_SUBSTITUTIONS:
            if k in initial_properties:
                pom_content = pom_content.replace("#{%s}" % k, initial_properties[k])
                del initial_properties[k]

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
        start_section_index = pom_template_content.find(TemplatePomGen.PROPERTIES_SECTION_START)
        if start_section_index == -1:
            parsed_properties = {}
        else:
            end_section_index = pom_template_content.index(TemplatePomGen.PROPERTIES_SECTION_END)
            properties_content = pom_template_content[start_section_index:end_section_index + len(TemplatePomGen.PROPERTIES_SECTION_END)]
            parsed_properties = pomparser.parse_version_properties(properties_content)
        start_section_index = pom_template_content.find(TemplatePomGen.DEPS_CONFIG_SECTION_START)
        if start_section_index == -1:
            return (pom_template_content, pomparser.ParsedDependencies(), parsed_properties)
        else:
            if TemplatePomGen.TRANSITIVE_DEPS_PROP_NAME not in pom_template_content and TemplatePomGen.UNUSED_CONFIGURED_DEPS_PROP_NAME not in pom_template_content:
                logger.error("Dependency customization section found but neither %s nor %s substitution is used. Dependency customization will be ignored." % TemplatePomGen.INITAL_PROPERTY_SUBSTITUTIONS)
            end_section_index = pom_template_content.index(TemplatePomGen.DEPS_CONFIG_SECTION_END)
            dynamic_deps_content = pom_template_content[start_section_index + len(TemplatePomGen.DEPS_CONFIG_SECTION_START):end_section_index]
            # make this a well formed pom
            dynamic_deps_content = "<project><dependencies>%s</dependencies></project>" % dynamic_deps_content
            parsed_dependencies = pomparser.parse_dependencies(dynamic_deps_content)
            # now that dependencies have been parsed, remove the special 
            # depdendency config section from pom template
            pom_template_content = pom_template_content[:start_section_index] + pom_template_content[end_section_index + len(TemplatePomGen.DEPS_CONFIG_SECTION_END)+1:]
            return (pom_template_content, parsed_dependencies, parsed_properties)

    def _get_version_properties(self, pomcontenttype, pom_template_parsed_properties):
        # the version of all dependencies can be referenced in a pom template
        # using the syntax: #{<groupId>:<artifactId>:[<classifier>:]version}.
        #
        # Additionally, versions of external dependencies may be referenced
        # using the dependency's "maven install" name, for example:
        # #{@maven//:com_google_guava_guava.version}
        # 
        # For convenience, we also support the unqualified maven install name,
        # without the leading repository name. This is useful when there are
        # many maven install rules, but they all reference the same maven 
        # artifact versions.

        #{<groupId>:<artifactId>:[<classifier>:]version} -> version value
        #{com_google_guava_guava.version} -> version value
        key_to_version = {}

        # internal bookeeping for this method
        key_to_dep = {}

        # the version of these dependencies may be referenced in the pom
        # template:
        # all external deps + deps built out of the monorepo that are
        # transitives of this library
        all_deps = \
            list(self._workspace.name_to_external_dependencies.values()) + \
            [d for d in self.dependencies_library_transitive_closure if d.bazel_package is not None]

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
            version_from_dep = self._dep_version(pomcontenttype, dep)
            key_to_version[key] = version_from_dep
            key_to_dep[key] = dep
            if dep.bazel_label_name is not None:
                key = "%s.version" % dep.bazel_label_name
                if key in key_to_version and version_from_dep != key_to_version[key]:
                    raise Exception("%s version: %s is already in versions, previous: %s" % (key, self._dep_version(pomcontenttype, dep), key_to_version[key]))
                key_to_version[key] = dep.version
                key_to_dep[key] = dep

                # we'll also allow usage of the unqualified label as a key
                # so "com_google_guava_guava" instead of
                # "@maven//:com_google_guava_guava"
                # this works well if the repository is setup in such a way
                # that all Maven artifacts have the same version, regardless
                # of which maven install rule they are managed by
                # if the versions differ, then the fully qualified label name
                # has to be used
                key_to_version["%s.version" % dep.unqualified_bazel_label_name] = dep.version

        # the maven coordinates of this artifact can be referenced directly:
        key_to_version["artifact_id"] = self._artifact_def.artifact_id
        key_to_version["group_id"] = self._artifact_def.group_id
        key_to_version["version"] = self._artifact_def_version(pomcontenttype)

        updated_properties = []
        group_version_dict = {}
        for parsed_property in pom_template_parsed_properties:
            property_name = parsed_property.get_property_name()
            property_value = parsed_property.get_property_value()
            templated = re.match('#{(.+)}', property_value)
            if templated:
                key = templated.group(1)
                version_property = pomparser.ParsedProperty(property_name, key_to_version[key])
                updated_properties.append(version_property)
                group_id = key_to_dep[key].group_id
                group_version_dict[group_id] = version_property
            else:
                updated_properties.add(parsed_property)
        return key_to_version, updated_properties, group_version_dict

    def _get_crawled_dependencies_properties(self, pomcontenttype, pom_template_parsed_deps, group_version_dict, substitute_version_properties):
        # this is somewhat lame: an educated guess on where the properties
        # being build here will be referenced (within 
        # project/dependencyManagement/dependencies)
        indent = _INDENT*3

        properties = {}
        if substitute_version_properties:
            updated_group_version_dict = pomproperties.get_group_version_dict(self.dependencies_library_transitive_closure, group_version_dict=group_version_dict)
        else:
            updated_group_version_dict = {}
        content = self._build_deps_property_content(
            self.dependencies_library_transitive_closure,
            pom_template_parsed_deps,
            pomcontenttype, indent, updated_group_version_dict)
        properties[TemplatePomGen.TRANSITIVE_DEPS_PROP_NAME] = content
        pom_template_only_deps = pom_template_parsed_deps.get_parsed_deps_set_missing_from(self.dependencies_library_transitive_closure)

        if substitute_version_properties:
            updated_group_version_dict = pomproperties.get_group_version_dict(pom_template_only_deps, group_version_dict=updated_group_version_dict)
        else:
            updated_group_version_dict = {}
        content = self._build_template_only_deps_property_content(\
            _sort(pom_template_only_deps),
            pom_template_parsed_deps,
            indent, updated_group_version_dict)
        properties[TemplatePomGen.UNUSED_CONFIGURED_DEPS_PROP_NAME] = content
        return properties, updated_group_version_dict

    def _build_template_only_deps_property_content(self, deps,
                                                   pom_template_parsed_deps,
                                                   indent, group_version_dict):
        content = ""
        for dep in deps:
            raw_xml = pom_template_parsed_deps.get_parsed_xml_str_for(dep)
            if dep.group_id in group_version_dict and dep.version == group_version_dict[dep.group_id].get_property_value():
                replace_version = group_version_dict[dep.group_id].get_property_name()
                raw_xml = raw_xml.replace(dep.version, "${%s}" % replace_version)
            content += pomparser.indent_xml(raw_xml, indent)
        content = content.rstrip()
        return content

    def _build_deps_property_content(self, deps, pom_template_parsed_deps, 
                                     pomcontenttype, indent, group_version_dict):
        content = ""
        deps = _sort(deps)
        for dep in deps:
            dep = self._copy_attributes_from_parsed_dep(dep, pom_template_parsed_deps)
            pom_template_exclusions = pom_template_parsed_deps.get_parsed_exclusions_for(dep)
            dep_has_exclusions = len(pom_template_exclusions) > 0
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=not dep_has_exclusions, group_version_dict=group_version_dict)
            if dep_has_exclusions:
                exclusions = list(pom_template_exclusions)
                exclusions.sort()
                group_and_artifact_ids = [(d.group_id, d.artifact_id) for d in exclusions]
                content, indent = self._gen_exclusions(content, indent, group_and_artifact_ids)
                content, indent = common.xml(content, "dependency", indent, close_element=True)

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

    Generates a pom.xml file based on the specified singleton (shared) template.

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

    def gen(self, pomcontenttype):
        content = self.pom_template.replace("#{group_id}", self._artifact_def.group_id)
        content = content.replace("#{artifact_id}", self._artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("#{version}", version)
        content = self._handle_description(content, self.pom_content.description)
        content = self._remove_token(content, "#{version_properties}")
        if len(self.dependencies) == 0:
            content = self._remove_token(content, "#{dependencies}")
        else:
            content = content.replace("#{dependencies}", self._gen_all_dependencies_sections(pomcontenttype))
        return content

    def _load_additional_dependencies_hook(self):
        return _query_dependencies(self._workspace, self._artifact_def,
                                   self._dependency)

    def _gen_all_dependencies_sections(self, pomcontenttype):
        dep_section = self._gen_dependencies(pomcontenttype)
        depman_section = self._gen_dep_management(pomcontenttype)
        return dep_section if depman_section is None else "%s\n%s" % (dep_section, depman_section)

    def _gen_dependencies(self, pomcontenttype):
        deps = self.dependencies
        if pomcontenttype == PomContentType.GOLDFILE:
            deps = list(deps)
            deps.sort()

        content = ""
        content, indent = common.xml(content, "dependencies", indent=_INDENT)
        for dep in deps:
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=False)
            # handle <exclusions>
            excluded_group_and_artifact_ids = [(d.group_id, d.artifact_id) for d in self._workspace.dependency_metadata.get_transitive_exclusions(dep)]
            excluded_group_and_artifact_ids += self._get_hardcoded_exclusions_for_dep(dep)
            if len(excluded_group_and_artifact_ids) > 0:
                content, indent = self._gen_exclusions(content, indent, excluded_group_and_artifact_ids)

            content, indent = common.xml(content, "dependency", indent, close_element=True)
        content, indent = common.xml(content, "dependencies", indent, close_element=True)
        return content

    def _gen_dep_management(self, pomcontenttype):
        """
        The transitives of the deps listed in the pom are added to
        to dependency management - this is to account for any version overrides
        that need to carry over to the Maven build.
        """
        deps = set(self.dependencies)
        transitives = set()
        for dep in deps:
            for transitive in self._workspace.dependency_metadata.get_transitive_closure(dep):
                if transitive in deps:
                    # if a dep is listed as <dependency> in the <dependencies>
                    # section, we won't add it also to <dependencyManagement>
                    pass
                else:
                    transitives.add(transitive)

        if len(transitives) == 0:
            return None

        sorted_transitives = sorted(transitives)

        content = ""
        content, indent = common.xml(content, "dependencyManagement", indent=_INDENT)
        content, indent = common.xml(content, "dependencies", indent, close_element=False)
        for dep in sorted_transitives:
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=False)
            content, indent = common.xml(content, "dependency", indent, close_element=True)
        content, indent = common.xml(content, "dependencies", indent, close_element=True)
        content, indent = common.xml(content, "dependencyManagement", indent, close_element=True)

        return content

    def _get_hardcoded_exclusions_for_dep(self, dep):
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
        if len(self.dependencies_artifact_transitive_closure) == 0:
            content = self._remove_token(content, "#{dependencies}")
            content = self._remove_token(content, "#{version_properties}")
        else:
            group_version_dict = pomproperties.get_group_version_dict(self.dependencies_artifact_transitive_closure)
            version_properties_content = pomproperties.gen_version_properties(group_version_dict)
            content = content.replace("#{version_properties}", version_properties_content)
            dep_man_content = self._gen_dependency_management(self.dependencies_artifact_transitive_closure, group_version_dict)
            content = content.replace("#{dependencies}", dep_man_content)

        # we assume the template specified <packaging>jar</packaging>
        # there's room for improvement here for sure
        expected_packaging = "<packaging>jar</packaging>"
        if not expected_packaging in content:
            raise Exception("The pom template must have %s" % expected_packaging)
        content = content.replace(expected_packaging, expected_packaging.replace("jar", "pom"))
        
        return content

    def _gen_dependency_management(self, deps, group_version_dict):
        content = ""
        content, indent = common.xml(content, "dependencyManagement", indent=_INDENT)
        content, indent = common.xml(content, "dependencies", indent)
        for dep in deps:
            content, indent = self._gen_dependency_element(PomContentType.RELEASE, dep, content, indent, close_element=True, group_version_dict=group_version_dict)
        content, indent = common.xml(content, "dependencies", indent, close_element=True)
        content, indent = common.xml(content, "dependencyManagement", indent, close_element=True)
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

    def register_dependencies_transitive_closure__artifact(self, d):
        self.pomgen.register_dependencies_transitive_closure__artifact(d)
        self.depmanpomgen.register_dependencies_transitive_closure__artifact(d)

    def register_dependencies_transitive_closure__library(self, d):
        self.pomgen.register_dependencies_transitive_closure__library(d)
        self.depmanpomgen.register_dependencies_transitive_closure__library(d)

    def gen(self, pomcontenttype):
        return self.pomgen.gen(pomcontenttype)

    def get_companion_generators(self):
        return (self.depmanpomgen,)

    def _load_additional_dependencies_hook(self):
        return self.pomgen._load_additional_dependencies_hook()


_INDENT = common.INDENT


def _sort(s):
    """
    Converts the specified set to a list, and returns the list, sorted.
    """
    assert isinstance(s, set), "Expected a set"
    l = list(s)
    l.sort()
    return l


# this method delegates to bazel query to get the value of a bazel target's 
# "deps" and "runtime_deps" attributes. it really doesn't belong in this module,
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

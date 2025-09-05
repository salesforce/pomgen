"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module contains pom.xml generation logic.
"""

import common.genmode as genmode
import copy
import crawl.pomcontent as pomcontentm
import generate.impl.pom.pomparser as pomparser
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


def get_pom_generator(pom_template, artifact_def, external_dependencies,
                      pom_content_md, dependency_md):
    """
    Returns a pom.xml generator (AbstractPomGen implementation) for the
    specified artifact_def.

    Arguments:
        pom_template: the template to use for generating dynamic (jar) pom.xmls
        artifact_def: the crawl.buildpom.MavenArtifactDef instance for access 
            to the parsed MVN-INF/* metadata files
        external_dependencies: all known external dependencies (jars)
        pom_content_md: additional metadata about pom content
        dependency_md: additional metadata about dependencies (jars)
    """
    assert artifact_def is not None
    assert isinstance(pom_content_md, pomcontentm.PomContent)
    mode = artifact_def.generation_mode
    if mode is genmode.DYNAMIC:
        also_generate_dep_man_pom = artifact_def.gen_dependency_management_pom
        if also_generate_dep_man_pom:
            return PomWithCompanionDependencyManagementPomGen(
                artifact_def, pom_template, pom_content_md, dependency_md)
        else:
            return DynamicPomGen(artifact_def, pom_template, pom_content_md, dependency_md)
    elif mode is genmode.TEMPLATE:
        return TemplatePomGen(artifact_def, external_dependencies, dependency_md)
    elif mode is genmode.SKIP:
        return NoopPomGen(artifact_def, dependency_md)
    else:
        raise Exception("Bug: unknown generation_mode [%s] for %s" % (mode, artifact_def.bazel_package))


class AbstractPomGen(object):

    def __init__(self, artifact_def, dependency_md):
        self._artifact_def = artifact_def
        self._dependency_md = dependency_md

        self.dependencies = set()
        self.dependencies_artifact_transitive_closure = set()
        self.dependencies_library_transitive_closure = set()

    @property
    def artifact_def(self):
        return self._artifact_def

    @property
    def bazel_package(self):
        return self._artifact_def.bazel_package

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

    def _xml_comment(self, comment, indent):
        """
        Returns a single line <!-- xml comment -->.
        """
        return "\n%s<!-- %s -->\n" % (' '*indent, comment)

    def _gen_dependency_element(self, pomcontenttype, dep, content, indent, close_element):
        """
        Generates a <dependency> element.

        Returns the generated content and the current identation level as a 
        tuple: (content, indent)

        This method is only intended to be called by subclasses.
        """
        content, indent = self._xml(content, "dependency", indent)
        content, indent = self._xml(content, "groupId", indent, dep.group_id)
        content, indent = self._xml(content, "artifactId", indent, dep.artifact_id)
        content, indent = self._xml(content, "version", indent, self._dep_version(pomcontenttype, dep))
        classifier = self._dependency_md.get_classifier(dep)
        if classifier is not None:
            content, indent = self._xml(content, "classifier", indent, classifier)
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
    A placeholder pom generator that doesn't generate anything, but still
    follows references.
    """
    def __init__(self, artifact_def, dependency_md):
        super(NoopPomGen, self).__init__(artifact_def, dependency_md)


class TemplatePomGen(AbstractPomGen):

    TRANSITIVE_DEPS_PROP_NAME = "pomgen.transitive_closure_of_library_dependencies"
    UNUSED_CONFIGURED_DEPS_PROP_NAME = "pomgen.unencountered_dependencies"
    DEPS_CONFIG_SECTION_START = "__pomgen.start_dependency_customization__"
    DEPS_CONFIG_SECTION_END = "__pomgen.end_dependency_customization__"

    # these properties need to be replaced first in pom templates
    # because their values may reference other properties
    INITAL_PROPERTY_SUBSTITUTIONS = (TRANSITIVE_DEPS_PROP_NAME,
                                     UNUSED_CONFIGURED_DEPS_PROP_NAME,)

    """
    Generates a pom.xml based on a template file.
    """
    def __init__(self, artifact_def, external_dependencies, dependency_md):
        super(TemplatePomGen, self).__init__(artifact_def, dependency_md)
        self._external_dependencies = external_dependencies

    def gen(self, pomcontenttype):
        pom_content = self.artifact_def.custom_pom_template_content
        pom_content, parsed_dependencies = self._process_pom_template_content(pom_content)

        properties = self._get_properties(pomcontenttype, parsed_dependencies)

        for k in TemplatePomGen.INITAL_PROPERTY_SUBSTITUTIONS:
            if k in properties:
                pom_content = pom_content.replace("#{%s}" % k, properties[k])
                del properties[k]

        for k in properties.keys():
            pom_content = pom_content.replace("#{%s}" % k, properties[k])

        bad_refs = [match.group(1) for match in re.finditer(r"""\#\{(.*?)\}""", pom_content) if len(match.groups()) == 1]
        if len(bad_refs) > 0:
            raise Exception("pom template [%s] has unresolvable references: %s" % (self._artifact_def, bad_refs))
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
        # using the dependency's "maven install" name, for example:
        # #{@maven//:com_google_guava_guava.version}
        # This name must be used if there are multiple dependencies,
        # from different maven_intall rules, that have the same group/artifact
        # ids but different versions.
        # 
        # For convenience, we also support the unqualified maven install name,
        # without the leading repository name. This is useful when there are
        # many maven_install rules, but they all reference the same maven 
        # artifact versions.
        #
        # name -> version
        key_to_version = {}

        # internal bookeeping for this method
        key_to_dep = {}

        # the version of these dependencies may be referenced in the pom
        # template:
        # all external deps + deps built out of the monorepo that are
        # transitives of this library
        all_deps = \
            list(self._external_dependencies) + \
            [d for d in self.dependencies_library_transitive_closure if d.bazel_package is not None]

        for dep in all_deps:
            key = self._get_unqual_ga_key(dep)
            version_ref_must_be_fq = False
            if key in key_to_version:
                conflicting_dep = key_to_dep[key]
                # check whether this conflict requires version refs to be fully
                # qualified or if it is fatal (method below raises)
                version_ref_must_be_fq = self._check_for_dep_conflict(dep, conflicting_dep)
                # remove unqualified names added for the conflicting dep
                del key_to_version[self._get_unqual_label_key(conflicting_dep)]
                del key_to_version[key]
            version_from_dep = self._dep_version(pomcontenttype, dep)
            if not version_ref_must_be_fq:
                # the key (groupId:artifactId:version) is not fully qualified,
                # only the name prefixed with the maven_install rule name is
                key_to_version[key] = version_from_dep
            key_to_dep[key] = dep
            if dep.bazel_label_name is not None:
                # this is fq name, leading with the maven_install name
                key = "%s.version" % dep.bazel_label_name
                if key in key_to_version and version_from_dep != key_to_version[key]:
                    raise Exception("%s version: %s is already in versions, previous: %s" % (key, self._dep_version(pomcontenttype, dep), key_to_version[key]))
                key_to_version[key] = dep.version
                key_to_dep[key] = dep

                if not version_ref_must_be_fq:
                    # we'll also allow usage of the unqualified label as a key
                    # so "com_google_guava_guava" instead of
                    # "@maven//:com_google_guava_guava"
                    # this works well if the repository is setup in such a way
                    # that all Maven artifacts have the same version, regardless
                    # of which maven install rule they are managed by
                    # if the versions differ, then the fully qualified label
                    # name has to be used
                    key_to_version[self._get_unqual_label_key(dep)] = dep.version

        # the maven coordinates of this artifact can be referenced directly:
        key_to_version["artifact_id"] = self._artifact_def.artifact_id
        key_to_version["group_id"] = self._artifact_def.group_id
        key_to_version["version"] = self._artifact_def_version(pomcontenttype)

        return key_to_version

    def _get_unqual_ga_key(self, dep):
        return "%s:version" % dep.maven_coordinates_name

    def _get_unqual_label_key(self, dep):
        return "%s.version" % dep.unqualified_bazel_label_name

    def _get_crawled_dependencies_properties(self, pomcontenttype, pom_template_parsed_deps):
        # this is somewhat lame: an educated guess on where the properties
        # being build here will be referenced (within 
        # project/depedencyManagement/dependencies)
        indent = _INDENT*3

        properties = {}

        content = self._build_deps_property_content(
            self.dependencies_library_transitive_closure,
            pom_template_parsed_deps,
            pomcontenttype, indent)
        properties[TemplatePomGen.TRANSITIVE_DEPS_PROP_NAME] = content

        pom_template_only_deps = pom_template_parsed_deps.get_parsed_deps_set_missing_from(self.dependencies_library_transitive_closure)
        content = self._build_template_only_deps_property_content(\
            _sort(pom_template_only_deps),
            pom_template_parsed_deps,
            indent)
        properties[TemplatePomGen.UNUSED_CONFIGURED_DEPS_PROP_NAME] = content

        return properties

    def _check_for_dep_conflict(self, dep1, dep2):
        """
        Returns False if there is actually no conflict because versions match,
        True, if there is a conflict but we can tolerate it, or raises if the
        conflict is fatal.
        """
        if dep1.bazel_package is None and dep2.bazel_package is None:
            # both deps are external
            if dep1.version == dep2.version:
                return False # no problem
            else:
                return True # we tolerate diff versions for ext deps
        elif dep1.bazel_package is not None and dep2.bazel_package is not None:
            # both deps are internal, it doesn't make sense to get here
            raise Exception("All internal dependencies must always be on the same versions! [%s] vs [%s]" % (dep1, dep2))

        return False

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
    Generates a pom.xm file based on the specified singleton (shared) template.

    The following placesholders must exist in the specified template:
       #{dependencies} - will be replaced with the <dependencies> section

    The following placesholders may exist in the specified template:

       #{artifact_id}
       #{group_id}
       #{version}
    """
    def __init__(self, artifact_def, pom_template, pom_content_md, dependency_md):
        super(DynamicPomGen, self).__init__(artifact_def, dependency_md)
        assert isinstance(pom_content_md, pomcontentm.PomContent)
        self.pom_template = pom_template
        self.pom_content_md = pom_content_md

    def gen(self, pomcontenttype):
        content = self.pom_template.replace("#{group_id}", self._artifact_def.group_id)
        content = content.replace("#{artifact_id}", self._artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("#{version}", version)
        content = self._handle_description(content, self.pom_content_md.description)
        if len(self.dependencies) == 0:
            content = self._remove_token(content, "#{dependencies}")
        else:
            content = content.replace(
                "#{dependencies}", self._gen_dependencies(pomcontenttype))
        return content

    def _gen_dependencies(self, pomcontenttype):
        content = ""
        content, indent = self._xml(content, "dependencies", indent=_INDENT)
        content += self._gen_dependencies_xml(pomcontenttype, self.dependencies, indent)

        # we also add the transitives of the deps to dependencies - this is to
        # account for any version overrides that need to carry over to the
        # Maven build.
        # this is done ONLY for 3rd party jars from maven_install files
        transitives = self._get_transitive_deps(self.dependencies)
        if len(transitives) > 0:
            content += self._xml_comment("The transitives of the dependencies above", indent)
            content += self._gen_dependencies_xml(pomcontenttype, transitives, indent)

        content, indent = self._xml(content, "dependencies", indent, close_element=True)
        return content

    def _gen_dependencies_xml(self, pomcontenttype, dependencies, indent):
        if pomcontenttype == PomContentType.GOLDFILE:
            dependencies = sorted(dependencies)
        content = ""
        for dep in dependencies:
            content, indent = self._gen_dependency_element(pomcontenttype, dep, content, indent, close_element=False)
            # handle <exclusions>
            # if a dep is built in the shared-repo, do not add any exclusions, they will do that themselves.
            if not dep.bazel_buildable:
                # exclude all transitives from <dependencies> as all transitives are already root level anyway
                excluded_group_and_artifact_ids = [("*", "*")]
                content, indent = self._gen_exclusions(content, indent, excluded_group_and_artifact_ids)
            content, indent = self._xml(content, "dependency", indent, close_element=True)
        return content

    def _get_transitive_deps(self, dependencies):
        """
        Given an iterable of dependency instances, returns all transitive
        dependencies, iff the input dependency is maven_install defined.
        """
        transitives = []
        transitives_set = set()
        dependencies_set = set(dependencies)
        for dep in dependencies:
            for transitive in self._dependency_md.get_transitive_closure(dep):
                if transitive not in self.dependencies_artifact_transitive_closure:
                    # this is to honor the "emitted_dependencies" filtering that
                    # can be defined in BUILD.pom files
                    # filtered deps are not in the "full transitives" list
                    continue
                if transitive in transitives_set:
                    # avoid duplication
                    pass
                elif transitive in dependencies_set:
                    # if a transitive is already listed as <dependency> in the
                    # <dependencies> section, we don't need to include it again
                    pass
                else:
                    transitives.append(transitive)
                    transitives_set.add(transitive)

        return transitives


class DependencyManagementPomGen(AbstractPomGen):
    """
    Generates a dependency management only pom, containing a
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
    def __init__(self, artifact_def, pom_template, pom_content_md, dependency_md):
        super(DependencyManagementPomGen, self).__init__(artifact_def, dependency_md)
        self.pom_template = pom_template
        self.pom_content_md = pom_content_md

    def gen(self, pomcontenttype):
        assert pomcontenttype == PomContentType.RELEASE
        content = self.pom_template.replace("#{group_id}", self._artifact_def.group_id)
        # by convention, we add the suffix ".depmanagement" to the artifactId
        # so com.blah is the real jar artifact and com.blah.depmanagement
        # is the dependency management pom for that artifact
        content = content.replace("#{artifact_id}", "%s.depmanagement" % self._artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("#{version}", version)
        content = self._handle_description(content, self.pom_content_md.description)
        if len(self.dependencies_artifact_transitive_closure) == 0:
            content = self._remove_token(content, "#{dependencies}")
        else:
            dep_man_content = self._gen_dependency_management(self.dependencies_artifact_transitive_closure)
            content = content.replace("#{dependencies}", dep_man_content)

        # we assume the template specified <packaging>jar</packaging>
        # there's room for improvement here for sure
        expected_packaging = "<packaging>jar</packaging>"
        if expected_packaging not in content:
            raise Exception("The pom template must have %s" % expected_packaging)
        content = content.replace(expected_packaging, expected_packaging.replace("jar", "pom"))
        
        return content

    def _gen_dependency_management(self, deps):
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
    def __init__(self, artifact_def, pom_template, pom_content_md, dependency_md):
        super(PomWithCompanionDependencyManagementPomGen, self).__init__(artifact_def, dependency_md)
        self.pomgen = DynamicPomGen(artifact_def, pom_template, pom_content_md, dependency_md)
        self.depmanpomgen = DependencyManagementPomGen(artifact_def, pom_template, pom_content_md, dependency_md)

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


_INDENT = pomparser.INDENT


def _sort(s):
    """
    Converts the specified set to a list, and returns the list, sorted.
    """
    the_list = list(s) if isinstance(s, set) else s
    the_list.sort()
    return the_list

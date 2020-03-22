"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module contains pom.xml generation logic.
"""

from common import pomgenmode
from common import mdfiles
import copy
from crawl import bazel
from crawl import pomparser
from crawl import workspace
import os
import re

class PomContentType:
    """
    Available pom content types:
      
      RELEASE - this is the default, standard pom.xml, based on  BUILD file or 
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

def get_pom_generator(workspace, pom_template, maven_artifact_def):
    mode = maven_artifact_def.pom_generation_mode
    if mode is pomgenmode.DYNAMIC:
        return DynamicPomGen(workspace, maven_artifact_def, pom_template)
    elif mode is pomgenmode.TEMPLATE:
        content, _ = mdfiles.read_file(workspace.repo_root_path,
                                       maven_artifact_def.bazel_package,
                                       maven_artifact_def.pom_template_file)
        return TemplatePomGen(workspace, maven_artifact_def, content)
    else:
        raise Exception("Unknown pom_generation_mode [%s] for %s" % (mode, maven_artifact_def))

class AbstractPomGen(object):
    def __init__(self, workspace, artifact_def):
        self.artifact_def = artifact_def
        self.workspace = workspace

    @property
    def bazel_package(self):
        return self.artifact_def.bazel_package

    def process_dependencies(self):
        """
        Discovers the dependencies of this artifact (bazel package).

        This method *must* be called before generating a pom.

        This method returns a tuple of 2 lists of Dependency instances: (l1, l2)
            l1: all source dependencies (== references to other bazel packages)
            l2: all external dependencies (maven jars)
        """
        all_deps = ()
        if self.artifact_def.deps is not None:
            all_deps = self.workspace.parse_dep_labels(self.artifact_def.deps)
        all_deps += self._load_additional_dependencies_hook()

        source_dependencies = []
        ext_dependencies = []
        for dep in all_deps:
            if dep.bazel_package is None:
                ext_dependencies.append(dep)
            else:
                source_dependencies.append(dep)
        
        return (source_dependencies, ext_dependencies)

    def _load_additional_dependencies_hook(self):
        """
        Returns a list of dependency instances referenced by the current 
        package.

        Only meant to be overridden by subclasses.
        """
        return ()

    def register_dependencies(self, crawled_bazel_packages, 
                              crawled_external_dependencies):
        """
        This method is called after all bazel packages have been crawled and
        processed, with the following sets of Dependency instances.

            - crawled_bazel_packages: 
                  a set of all crawled bazel packages
            - crawled_external_dependencies: 
                  a set of all crawled (discovered) external dependencies

        Subclasses that care about this must implement this method and
        do something with the argument passed into this method.
        """
        pass

    def gen(self, pomcontenttype=PomContentType.RELEASE):
        """
        Returns the generated pom.xml as a string.  This method may be called
        multiple times, and must therefore be idempotent.
        """
        raise Exception("must be implemented by subclass")

    def _artifact_def_version(self, pomcontenttype):
        """
        Returns the associated artifact's version, based on the specified 
        PomContentType.

        This is a utility method for subclasses.
        """
        return PomContentType.MASKED_VERSION if pomcontenttype is PomContentType.GOLDFILE else self.artifact_def.version

    def _dep_version(self, pomcontenttype, dep):
        """
        Returns the given dependency's version, based on the specified
        PomContentType.

        This is a utility method for subclasses.
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

        This is a utility method for subclasses.
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
        content, indent = self._xml(content, "exclusions", indent)
        for ga in group_and_artifact_ids:
            content, indent = self._xml(content, "exclusion", indent)
            content, indent = self._xml(content, "groupId", indent, ga[0])
            content, indent = self._xml(content, "artifactId", indent, ga[1])
            content, indent = self._xml(content, "exclusion", indent, close_element=True)
        content, indent = self._xml(content, "exclusions", indent, close_element=True)
        return content, indent

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
    def __init__(self, workspace, artifact_def, template_content):
        super(TemplatePomGen, self).__init__(workspace, artifact_def)
        self.template_content = template_content
        self.crawled_bazel_packages = set()
        self.crawled_external_dependencies = set()

    def register_dependencies(self, crawled_bazel_packages, crawled_external_dependencies):
        self.crawled_bazel_packages = crawled_bazel_packages
        self.crawled_external_dependencies = crawled_external_dependencies

    def gen(self, pomcontenttype=PomContentType.RELEASE):
        pom_content, parsed_dependencies = self._process_pom_template_content(self.template_content)

        properties = self._get_properties(pomcontenttype, parsed_dependencies)

        for k in TemplatePomGen.INITAL_PROPERTY_SUBSTITUTIONS:
            if k in properties:
                pom_content = pom_content.replace("#{%s}" % k, properties[k])
                del properties[k]

        for k in properties.keys():
            pom_content = pom_content.replace("#{%s}" % k, properties[k])

        bad_refs = [match.group(1) for match in re.finditer(r"""\#\{(.*?)\}""", pom_content) if len(match.groups()) == 1]
        if len(bad_refs) > 0:
            raise Exception("pom template for [%s] has unresolvable references: %s" % (self.artifact_def, bad_refs))
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

        properties = {}

        all_deps = list(self.workspace.name_to_external_dependencies.values())+\
            list(self.crawled_bazel_packages)
        for dep in all_deps:
            key = "%s:version" % dep.maven_coordinates_name
            if key in properties:
                msg = "Found multiple artifacts with the same groupId:artifactId: \"%s\". This means that there are either multiple BUILD.pom files defining the same artifact, or that a BUILD.pom defined artifact has the same groupId and artifactId as a referenced Nexus jar" % dep.maven_coordinates_name
                raise Exception(msg)
            properties[key] = self._dep_version(pomcontenttype, dep)
            if dep.bazel_label_name is not None:
                key = "%s.version" % dep.bazel_label_name
                assert key not in properties
                properties[key] = dep.version

        # the maven coordinates of this artifact can be referenced directly:
        properties["artifact_id"] = self.artifact_def.artifact_id
        properties["group_id"] = self.artifact_def.group_id
        properties["version"] = self._artifact_def_version(pomcontenttype)

        return properties

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

    Generates a pom.xm file from scratch.
    """
    def __init__(self, workspace, artifact_def, pom_template):
        super(DynamicPomGen, self).__init__(workspace, artifact_def)
        self.pom_template = pom_template
        self.dependencies = None

    def _load_additional_dependencies_hook(self):
        if not self.artifact_def.include_deps:
            self.dependencies = ()
        else:
            try:
                dep_labels = bazel.query_java_library_deps_attributes(
                    self.workspace.repo_root_path,
                    self.artifact_def.bazel_package)
                deps = self.workspace.parse_dep_labels(dep_labels)
                deps = self.workspace.normalize_deps(self.artifact_def, deps)
                # keep a reference to all the deps - we need them during pom
                # generation
                self.dependencies = deps
            except Exception as e:
                raise Exception("Error while processing dependencies: %s %s caused by %s" % (e.message, self.artifact_def, repr(e)))

        return self.dependencies

    def gen(self, pomcontenttype=PomContentType.RELEASE):
        content = self.pom_template.replace("${group_id}", self.artifact_def.group_id)
        content = content.replace("${artifact_id}", self.artifact_def.artifact_id)
        version = self._artifact_def_version(pomcontenttype)
        content = content.replace("${version}", version)
        content = content.replace("${dependencies}", self._gen_dependencies(pomcontenttype))
        return content

    def _gen_dependencies(self, pomcontenttype):
        if len(self.dependencies) == 0:
            return ""

        deps = self.dependencies
        if pomcontenttype == PomContentType.GOLDFILE:
            deps = self.dependencies[:]
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

_INDENT = pomparser.INDENT

def _sort(s):
    """
    Converts the specified set to a list, and returns the list, sorted.
    """
    assert isinstance(s, set), "Expected a set"
    l = list(s)
    l.sort()
    return l

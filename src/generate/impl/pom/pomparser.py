"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This is a helper module for pom generation - it contains methods dealing with
pom.xml parsing.
"""
import collections
import generate.impl.pom.dependency as dependencym
import os
import xml.etree.ElementTree as ET


# https://docs.python.org/3/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
XML_NS = "{http://maven.apache.org/POM/4.0.0}"

# this is the indentation used when writing out pom content, including content
# for pom templates
INDENT = 4 # spaces


def format_for_comparison(pom_content):
    """
    Returns the pom as a string without:
        - comments
        - superfluous whitespace
        - the root <description> element
    """
    # Register namespace to avoid ns0 prefixes
    ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')

    tree = ET.fromstring(pom_content.encode().strip())

    # remove <description>, if it exists
    description_el = tree.find(XML_NS + "description")
    if description_el is not None:
        tree.remove(description_el)

    # remove comments recursively
    _remove_comments(tree)

    return _pretty_str(tree)


def indent_xml(xml_content, indent):
    indented_xml = ""
    current_indent = indent
    for line in xml_content.splitlines():
        line = line.strip()
        handled_indent = False
        if line.startswith("</"):
            current_indent -= INDENT
            handled_indent = True
        indented_xml += (' '*current_indent) + line + os.linesep
        if not handled_indent and line.startswith("<") and "</" not in line:
            current_indent += INDENT
            handled_indent = True
    return indented_xml


class ParsedDependencies:

    def __init__(self, dependencies=set(), dependency_to_exclusions=collections.defaultdict(list), dependency_to_str_repr={}):
        # a set of all dependencies (Dependency instances) declared in the 
        # pom's DependencyManagement section
        self._dependencies = dependencies

        # a mapping of a Dependency instance, to a list of all its declared 
        # exclusions. the exclusions are also Dependency instances
        self._dependency_to_exclusions = dependency_to_exclusions

        # a mapping of a Dependency instance to its string xml representation
        self._dependency_to_str_repr = dependency_to_str_repr

    def get_parsed_exclusions_for(self, dependency):
        """
        Returns the exclusions for the specified dependency that were parsed
        out of a pom template.
        The exclusions are returned as a list of Dependency instances.
        """
        parsed_dep = self.get_parsed_dependency_for(dependency)
        return () if parsed_dep is None else self._dependency_to_exclusions[parsed_dep]

    def get_parsed_xml_str_for(self, dependency):
        """
        Returns the raw, unformatted xml string of the specified dependency, as
        it was read out of a pom template.
        """
        parsed_dep = self.get_parsed_dependency_for(dependency)
        return None if parsed_dep is None else self._dependency_to_str_repr[parsed_dep]

    def get_parsed_dependency_for(self, dependency):
        """
        Because of the way Dependency implements equality, we do a lookup
        using artifactId and groupId
        """
        for d in self._dependencies:
            if (d.artifact_id == dependency.artifact_id and 
                d.group_id == dependency.group_id):
                return d
        return None

    def get_parsed_deps_set_missing_from(self, *args):
        """
        Because of the way Dependency implements equality, we use only 
        artifactId and groupId here to compare Dependency instances.
        """
        specified = set()
        for _set in args:
            for d in _set:
                specified.add((d.group_id, d.artifact_id))
        missing = set()
        for d in self._dependencies:
            if ((d.group_id, d.artifact_id)) not in specified:
                missing.add(d)
        return missing


def parse_dependencies(pom_content):
    """
    Parses the <dependencies> section in the specified pom_content.

    Returns a ParsedDependencies instance.
    """
    # Register namespace to avoid ns0 prefixes
    ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')

    if pom_content.startswith("<project xmlns"):
        # lets not deal with the xml ns complication
        i = pom_content.index(">")
        pom_content = "<project" + pom_content[i:]

    tree = ET.fromstring(pom_content.encode().strip())
    dependencies_el = tree.find('dependencies')
    all_deps = list(dependencies_el) if dependencies_el is not None else []

    dependencies = set()
    dependency_to_exclusions = collections.defaultdict(list)
    dependency_to_str_repr = {}

    for el in all_deps:
        dep = _get_dependency_from_xml_element(el, version_must_be_set=True)
        dependency_to_str_repr[dep] = _get_unindented_xml(el)
        dependencies.add(dep)
        exclusions_el = el.find("exclusions")
        if exclusions_el is not None:
            for excl_el in exclusions_el:
                excluded_dep = _get_dependency_from_xml_element(excl_el, version_must_be_set=False)
                dependency_to_exclusions[dep].append(excluded_dep)

    return ParsedDependencies(dependencies, dependency_to_exclusions, dependency_to_str_repr)


def _get_dependency_from_xml_element(el, version_must_be_set):
    group_id = _get_element_text(el, "groupId", True)
    artifact_id = _get_element_text(el, "artifactId", True)
    version = _get_element_text(el, "version", version_must_be_set)
    classifier = _get_element_text(el, "classifier", False)
    scope = _get_element_text(el, "scope", False)
    _type = _get_element_text(el, "type", False)
    if _type is not None:
        # we currently don't support "type" (for no particular reason, we could)
        raise Exception("we are dropping type on the floor %s" % _str(el))

    return dependencym.PomDependency.init_with_components(
        group_id, artifact_id, version, packaging=None,
        classifier=classifier, scope=scope,
        maven_install_name=None,
        version_must_be_set=version_must_be_set)


def _pretty_str(el):
    """Format XML element with indentation."""
    ET.indent(el, space="  ")
    return _str(el) + "\n"


def _str(el):
    """Convert XML element to string."""
    return ET.tostring(el, encoding='unicode')


def _get_element_text(el, tag_name, must_not_be_empty):
    """Get text content of a child element."""
    child = el.find(tag_name)
    text = child.text.strip() if child is not None and child.text else None
    if must_not_be_empty and text is None:
        raise Exception("value of %s cannot be empty for %s" % (tag_name, _str(el)))
    return text


def _remove_comments(element):
    """Recursively remove all comments from an element tree."""
    # Comments in ElementTree have a callable tag (comment function)
    # We need to remove them from parent elements
    for parent in element.iter():
        # Create a list of children to keep (non-comments)
        children_to_keep = []
        for child in list(parent):
            if not callable(child.tag) and child.tag != ET.Comment:
                children_to_keep.append(child)
                _remove_comments(child)

        # Remove all children and re-add only the ones to keep
        parent[:] = children_to_keep


def _get_unindented_xml(element):
    xml = ""
    for line in _pretty_str(element).splitlines():
        xml += line.strip() + os.linesep
    return xml

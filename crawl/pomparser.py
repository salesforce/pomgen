"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This is a helper module for pom generation - it contains methods dealing with 
pom.xml parsing.
"""
from collections import defaultdict
from crawl import dependency
import os
try:
    from lxml import etree
except ImportError as ex:
    print('Module lxml is not installed, please execute the following in your environment:')
    print('$ pip install --user lxml')
    raise ex

# https://lxml.de/tutorial.html#namespaces
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
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.XML(pom_content.encode().strip(), parser=parser)

    # remove <description>, if it exists
    description_el = tree.find(XML_NS + "description")
    if description_el is not None:
        tree.remove(description_el)

    # remove comments
    comments = tree.xpath("//comment()")
    for c in comments:
        p = c.getparent()
        if p is not None:
            p.remove(c)

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
        if not handled_indent and line.startswith("<") and not "</" in line:
            current_indent += INDENT
            handled_indent = True
    return indented_xml

class ParsedDependencies:

    def __init__(self, dependencies=set(), dependency_to_exclusions=defaultdict(list), dependency_to_str_repr={}):
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
            if not ((d.group_id, d.artifact_id)) in specified:
                missing.add(d)
        return missing

def parse_dependencies(pom_content):
    """
    Parses the <dependencies> section in the specified pom_content.
    
    Returns a ParsedDependencies instance.
    """
    if pom_content.startswith("<project xmlns"):
        # lets not deal with the xml ns complication
        i = pom_content.index(">")
        pom_content = "<project" + pom_content[i:]

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.XML(pom_content.encode().strip(), parser=parser)
    all_deps = tree.xpath('/project/dependencies/*')

    dependencies = set()
    dependency_to_exclusions = defaultdict(list)
    dependency_to_str_repr = {}

    for el in all_deps:
        dep = _get_dependency_from_xml_element(el, version_must_be_set=True)
        dependency_to_str_repr[dep] = _get_unindented_xml(el)
        dependencies.add(dep)
        exclusions = el.xpath("exclusions/*")
        for el in exclusions:
            excluded_dep = _get_dependency_from_xml_element(el, version_must_be_set=False)
            dependency_to_exclusions[dep].append(excluded_dep)

    return ParsedDependencies(dependencies, dependency_to_exclusions, dependency_to_str_repr)

def _get_dependency_from_xml_element(el, version_must_be_set):
    group_id = _get_xpath_text_value(el, "groupId/text()", True)
    artifact_id = _get_xpath_text_value(el, "artifactId/text()", True)
    version = _get_xpath_text_value(el, "version/text()", version_must_be_set)
    classifier = _get_xpath_text_value(el, "classifier/text()", False)
    scope = _get_xpath_text_value(el, "scope/text()", False)
    _type = _get_xpath_text_value(el, "type/text()", False)
    if _type is not None:
        # we currently don't support "type" (for no particular reason, we could)
        raise Exception("we are dropping type on the floor %s" % _str(el))

    return dependency.ThirdPartyDependency(bazel_label_name=None, 
                                           group_id=group_id, 
                                           artifact_id=artifact_id, 
                                           version=version,
                                           classifier=classifier,
                                           scope=scope)

def _pretty_str(el):
    return _str(el, pretty=True)

def _str(el, pretty=False):
    return etree.tostring(el, pretty_print=pretty).decode()

def _get_xpath_text_value(el, xpath, must_not_be_empty):
    v = el.xpath(xpath)
    text = v[0].strip() if len(v) == 1 else None
    if must_not_be_empty and text is None:
        raise Exception("value of %s cannot be empty for %s" % (xpath, _str(el)))
    return text

def _get_unindented_xml(element):
    xml = ""
    for line in _pretty_str(element).splitlines():
        xml += line.strip() + os.linesep
    return xml

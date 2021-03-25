"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This is a helper module for pom property generation - it contains methods that create version properties
content based on groupId.
"""
from common import common
from crawl import pomparser
import re

_INDENT = common.INDENT

def get_group_version_dict(deps, group_version_dict={}):
    """
    Processes a list of Dependency instances, and optionally a mapping from groupId to ParsedProperty instance.
    If multiple artifacts with same groupId have different versions, this will create a version property for
    the first artifact parsed. If a version property for a groupId already exists in the group_version_dict
    from input, then it won't create a new property for that groupId.

    Returns a mapping from groupId to ParsedProperty instance.
    """
    content = ""
    result_group_version_dict = dict(group_version_dict)
    for dep in deps:
        group_id = dep.group_id
        version = dep.version
        if group_id not in result_group_version_dict:
            if re.match('#{(.+)}', version) or re.match('\${(.+)}', version):
                continue
            result_group_version_dict[group_id] = pomparser.ParsedProperty("%s.version" % group_id, version)
    return result_group_version_dict

def gen_version_properties(group_version_dict, pom_content = ""):
    """
    Processes a mapping from groupId to ParsedProperty instance, and optionally a pom content.
    This method generate version property pom content for the ParsedProperty instances in group_version_dict,
    if it does not already exist in pom_content.

    Returns a string with the pom content containing multiple version properties.
    """
    group_version_properties = list(group_version_dict.values())
    sorted_group_version_properties = sorted(group_version_properties, key=lambda x: x.get_property_name())
    content = ""
    indent = _INDENT*2
    for version_property in sorted_group_version_properties:
        property_name = version_property.get_property_name()
        property_value = version_property.get_property_value()
        if "<%s>" % property_name not in pom_content:
            content, indent = common.xml(content, property_name, indent, property_value)
    return content

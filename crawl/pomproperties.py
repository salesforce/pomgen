from common import common
from crawl import pomparser

_INDENT = common.INDENT

def get_group_version_dict(deps, group_version_dict={}):
    content = ""
    result_group_version_dict = dict(group_version_dict)
    for dep in deps:
        group_id = dep.group_id
        version = dep.version
        if not group_id in result_group_version_dict:
            result_group_version_dict[group_id] = pomparser.ParsedProperty("%s.version" % group_id, version)
    return result_group_version_dict

def gen_version_properties(group_version_dict, pom_content = ""):
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

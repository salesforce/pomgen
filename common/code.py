"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Helper functions used for parsing Python code (BUILD.pom[.released] files)
"""

import re


def get_function_block(code, function_name):
    """
    Simplistic string manipulation to find single function call 'block', for
    example:
    
        maven_artifact(
            "group", 
            "artifact", 
            "version"
        )

    The logic below assumes the character ')' doesn't appear anywhere in the 
    function name or arguments.
    """
    start = code.index(function_name)
    end = code.index(")", start + len(function_name))
    return code[start:end+1]


def get_attr_value(attr_name, the_type, dflt, content):
    """
    Given a string of "key = value" pair(s), specified as content, returns
    the value of the specified attr_name as the specified type (the_type).

    If the given attr_name is not found, returns the specified default (dflt).
    """
    if the_type is str:
        # uses " or ' as value anchors
        attr_expr = re.compile("""\s*%s\s*=\s*["'](.*)["']\s*""" % attr_name, re.MULTILINE)
    elif the_type is list:
        # uses [] or () as value anchors
        attr_expr = re.compile("""\s*%s\s*=\s*[\[\(](.*)[\]\)]\s*""" % attr_name, re.MULTILINE)
    elif the_type is bool:
        # since bool, we can just check for the exepcted values
        attr_expr = re.compile("""\s*%s\s*=\s*([Tt]rue|[Ff]alse)\s*""" % attr_name, re.MULTILINE)
    else:
        raise Exception("Unhandled type %s, type must be one of %s" % (the_type, (str, list, bool)))
    m = re.search(attr_expr, content)
    if m is None:
        return dflt
    value = m.group(1).strip()
    if the_type is str:
        return value
    elif the_type is list:
        l = []
        if len(value) > 0:
            for item in value.split(","):
                item = item.strip()
                if item.startswith("'") or item.startswith('"'):
                    item = item[1:]
                if item.endswith("'") or item.endswith('"'):
                    item = item[0:-1]
                l.append(item)
        return l
    else: # bool
        return True if value.lower() == "true" else False

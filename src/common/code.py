"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Helper functions used for parsing BUILD.pom[.released] files.
"""

import ast


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
    start = code.find(function_name)
    if start == -1:
        return None
    if not _has_only_space_in_front(code, start):
        return None
    if not _has_space_until_open_paren(code, start + len(function_name)):
        return None
    end = code.index(")", start + len(function_name))
    return code[start:end+1]


def parse_attributes(content):
    """
    Given a str of content like this:

    some_rule_name(
        a = True,
        b = ["my things"],
        c = 1,
        d = "value"
    )

    Returns a dict of attr_name -> value, so for the example above:
    {"a": True,
     "b": ["my_things"],
     "c": 1,
     "d": "value"}
    """
    attributes = {}
    equals_index = content.find("=")
    while equals_index != -1:
        name_start_index = _find_name_start_index(content, equals_index)
        name = content[name_start_index:equals_index].strip()
        value_start_index, value_end_index =\
            _find_value_start_and_end_index(content[equals_index:])
        value_start_index += equals_index
        value_end_index += equals_index
        value = ast.literal_eval(content[value_start_index:value_end_index])
        attributes[name] = value
        equals_index = content.find("=", value_end_index)
    return attributes


def _find_value_start_and_end_index(content):
    assert content[0] == "="
    within_string = False
    list_level = 0 # counter for nested lists
    function_level = 0 # counter for nested functions
    dict_level = 0 # counter for nested dictionaries: {}
    is_target_end = False
    value_start_index = -1
    for i in range(1, len(content)):
        if value_start_index == -1:
            if content[i] in (" ", "\t",):
                continue
            else:
                value_start_index = i

        if content[i] in ("'", '"',):
            if list_level + function_level == 0 + dict_level == 0:
                within_string = not within_string
        if content[i] == "[":
            if not within_string and function_level + dict_level  == 0:
                list_level += 1
        elif content[i] == "]":
            if not within_string and function_level + dict_level == 0:
                assert list_level > 0, content
                list_level -= 1
        elif content[i] == "{":
            if not within_string and function_level + list_level == 0:
                dict_level += 1
        elif content[i] == "}":
            if not within_string and function_level + list_level == 0:
                assert dict_level > 0, content
                dict_level -= 1
        elif content[i] == "(":
            if not within_string and list_level + dict_level == 0:
                function_level += 1
        elif content[i] == ")":
            if not within_string and list_level + dict_level == 0:
                if function_level > 0:
                    function_level -= 1
                else:
                    is_target_end = True # the paren that closes the target
        if content[i] == "," or is_target_end:
            if (not within_string and 
                list_level == 0 + function_level == 0 + dict_level == 0):
                # check for closing char
                for j in range(i-1, 0, -1):
                    if content[j] in ("'", '"',):
                        # include ending quote
                        return value_start_index, j+1
                    if content[j] in ("]", ")", "}",):
                        # include function/list closing char
                        return value_start_index, j+1
                # the value is an identifer, for example: deps = deps
                return value_start_index, i
    return value_start_index, i


def _find_target_end(content, start_target_index):
    paren_nesting_level = 1
    i = start_target_index
    while paren_nesting_level != 0:
        if content[i] == "(":
            paren_nesting_level += 1
        elif content[i] == ")":
            paren_nesting_level -=1
        i += 1
    return i


def _find_name_start_index(content, equals_index):
    within_name = False
    for i in range(equals_index-1, 0, -1):
        if content[i] in (" ", "\t", "\n"):
            if within_name:
                return i + 1
        else:
            if not within_name:
                within_name = True


def _has_only_space_in_front(text, start_index):
    if start_index < 0 or start_index >= len(text):
        raise IndexError("start_index is out of bounds")
    current_index = start_index
    while current_index > 0:
        current_index -= 1
        char = text[current_index]
        if char == '\n':
            return True
        if not char.isspace():
            return False
    return True


def _has_space_until_open_paren(text, start_index):
    if start_index < 0 or start_index >= len(text):
        raise IndexError("start_index is out of bounds")
    current_index = start_index
    while current_index < len(text):
        char = text[current_index]
        if char == '(':
            return True
        if not char.isspace():
            return False
        current_index += 1
    return False

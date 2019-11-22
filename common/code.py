"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Helper functions used for parsing Python code (BUILD.pom[.released] files)
"""

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


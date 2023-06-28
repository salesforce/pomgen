"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module contains one-offs related to version string processing.
"""

from . import code
import re


version_re = re.compile("(^.*version *= *[\"'])(.*?)([\"'].*)$", re.S)


def parse_build_pom_version(build_pom_content):
    """
    Returns the value of maven_artifact.version.
    """
    m = version_re.search(build_pom_content)
    if m is None:
        # possible if pom_generation_mode=skip
        return None
    else:
        return m.group(2).strip()


def parse_build_pom_released_version(build_pom_released_content):
    """
    Returns the value of released_maven_artifact.version.
    """
    return parse_build_pom_version(build_pom_released_content)

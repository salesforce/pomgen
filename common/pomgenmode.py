"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

def from_string(pomgenmode_string):
    """
    Returns a PomGenMode instance for the specified string value of 
    `pom_generation_mode`.
    """
    if pomgenmode_string is None:
        return DEFAULT
    for mode in ALL_MODES:
        if pomgenmode_string == mode.name:
            return mode
    raise Exception("Unknown pom_generation_mode: %s" % pomgenmode_string)


class PomGenMode:
    """
    The pom generation mode, as specified by the `pom_generation_mode` attribute
    of the `maven_artifact` rule.
    """
    def __init__(self, name, requires_mvn_art_update_rule):
        """
        name:
          The name of this pom_generation_mode
        requires_mvn_art_update_rule:
          Whether the BUILD.pom file for this mode requires the
          `maven_artifact_update` rule to be specified.
        """
        self.name = name
        self.requires_maven_artifact_update_rule = requires_mvn_art_update_rule

    def __str__(self):
        return "PomGenMode: %s" % self.name

    __repr__ = __str__


# dynamic: the pom is generated from scratch, using a common base template
DYNAMIC = PomGenMode("dynamic", requires_mvn_art_update_rule=True)

# template: the pom is generated based on a custom template file
TEMPLATE = PomGenMode("template", requires_mvn_art_update_rule=True)

DEFAULT = DYNAMIC
ALL_MODES = (DYNAMIC, TEMPLATE,)

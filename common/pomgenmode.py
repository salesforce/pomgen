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
        raise Exception("pom_generation_mode must be specified")
    for mode in ALL_MODES:
        if pomgenmode_string == mode.name:
            return mode
    raise Exception("Unknown pom_generation_mode: %s" % pomgenmode_string)


class PomGenMode:
    """
    The pom generation mode, as specified by the `pom_generation_mode` attribute
    of the `maven_artifact` rule.
    """
    def __init__(self, name, produces_artifact):
        """
        name:
          The name of this pom_generation_mode
        produces_artifact:
          Whether this pomgen mode produces a maven artifact
        """
        self.name = name
        self.produces_artifact = produces_artifact

    def __str__(self):
        return self.name

    __repr__ = __str__


# the pom is generated from scratch, using a common skeleton base template
# "interesting" pom content is only the <dependencies> section, which is based
# on BUILD file content
DYNAMIC = PomGenMode("dynamic", produces_artifact=True)

# the pom is generated based on a custom template file only
TEMPLATE = PomGenMode("template", produces_artifact=True)

# this bazel package is skipped over at pom generation time
# dependencies from this bazel package are "pushed up" to the closest parent
# that has an artifact producing pom_generation_mode
SKIP = PomGenMode("skip", produces_artifact=False)


DEFAULT = DYNAMIC
ALL_MODES = (DYNAMIC, TEMPLATE, SKIP,)

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import types

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

    The following attributes are available:
        name:
          The name of this pom_generation_mode

        produces_artifact:
          Whether this pomgen mode produces a maven artifact

        bazel_produced_artifact:
          Whether this pomgen mode represents an artifact that is built by
          Bazel (ie a jar)

        additional_dependency_attrs:
          The rule attributes that point to other dependencies to process.
          For all pomgen modes, these attributes are "deps" and "runtime_deps".
          Additional attributes may be added using this parameter
    """
    def __init__(self, name, produces_artifact, additional_dependency_attrs=()):
        """
        """
        self.name = name
        self.produces_artifact = produces_artifact
        self.dependency_attributes =\
            ("deps", "runtime_deps") + tuple(additional_dependency_attrs)

        def bazel_produced_artifact(self, pom_template_content):
            raise Exception("Method must be implemented")

    def __str__(self):
        return self.name

    __repr__ = __str__


# the pom is generated from scratch, using a common skeleton base template
# dynamic pom content is only the <dependencies> section, which is based on
# BUILD file content
DYNAMIC = PomGenMode("dynamic", produces_artifact=True,)
DYNAMIC.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: True, DYNAMIC)


# the pom is generated based on a custom template file only
TEMPLATE = PomGenMode("template", produces_artifact=True,)
# this is an edge case - for custom pom templates, the packaging tends to be
# "pom" - that's the whole point. but we have a couple of cases with different
# values (such as maven-plugin), in which case bazel is expected to build
# something also
TEMPLATE.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: pom_template_content.find("<packaging>pom</packaging>") == -1, TEMPLATE)


# this bazel package is skipped over at pom generation time
# dependencies from this bazel package are "pushed up" to the closest parent
# that has an artifact producing pom_generation_mode
SKIP = PomGenMode("skip", produces_artifact=False,
                  additional_dependency_attrs=("exports",))
SKIP.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: False, SKIP)


DEFAULT = DYNAMIC
ALL_MODES = (DYNAMIC, TEMPLATE, SKIP,)

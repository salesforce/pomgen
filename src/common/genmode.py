"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""
import types


def from_string(generation_mode_string):
    """
    Returns a GenerationMode instance matching the specified string.
    """
    assert generation_mode_string is not None

    for mode in ALL_USER_MODES:
        if generation_mode_string == mode.name:
            return mode
    raise Exception("Unknown generation_mode: %s" % generation_mode_string)


class GenerationMode:
    """
    The generation mode associated with artifact metadata.


    The following attributes are available:

        name:
          The name of this generation_mode

        produces_artifact:
          Whether this generation mode produces a artifact (for example a maven
          jar, pom or a python wheel)

        bazel_produced_artifact:
          Whether the artifact is built by bazel

        query_dependency_attributes:
          Whether to query the rule attributes that point to other dependencies
          (and whether to crawl those dependencies, since that's why we query
          them)

        additional_dependency_attrs:
          The rule attributes that point to other dependencies to process.
          For all generation modes, these attributes are "deps" and
          "runtime_deps".
          Additional attributes may be added using this attribute.
    """
    def __init__(self, name, produces_artifact, query_dependency_attributes,
                 additional_dependency_attrs=()):
        self.name = name
        self.produces_artifact = produces_artifact
        self.query_dependency_attributes = query_dependency_attributes
        self.dependency_attributes =\
            ("deps", "runtime_deps") + tuple(additional_dependency_attrs)

        def bazel_produced_artifact(self, pom_template_content):
            raise Exception("Method must be implemented")

    def __str__(self):
        return self.name

    __repr__ = __str__


# the manifest is generated from scratch, using a repository-wide common base
# template
DYNAMIC = GenerationMode("dynamic", produces_artifact=True,
                         query_dependency_attributes=True)
DYNAMIC.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: True, DYNAMIC)


# the manifest is generated based on a custom template file only
TEMPLATE = GenerationMode("template", produces_artifact=True,
                          # False here because pom templates may or may not
                          # have a BUILD file - if there is one, it
                          # is generally not related to the template
                          query_dependency_attributes=False)
# this is a hack for custom pom templates - their packaging tends to be
# "pom" - that's the whole point. but we have a couple of cases with different
# values (such as maven-plugin), in which case bazel is expected to build
# something also
TEMPLATE.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: pom_template_content.find("<packaging>pom</packaging>") == -1, TEMPLATE)


# this bazel package is skipped over at manifest generation time
# dependencies from this bazel package are "pushed up" to the closest parent
# that has an artifact producing generation_mode
SKIP = GenerationMode("skip", produces_artifact=False,
                      query_dependency_attributes=True,
                      additional_dependency_attrs=("exports",))
SKIP.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: False, SKIP)


# this generation mode is like "dynamic" but for a module that uses bazel's
# 1:1:1 structure (many bazel child packages)
DYNAMIC_ONEONEONE = GenerationMode("dynamic_111", produces_artifact=True,
                                   query_dependency_attributes=True)
DYNAMIC_ONEONEONE.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: True, DYNAMIC_ONEONEONE)


# this generation mode marks a bazel child bazel package in a 1:1:1 enabled
# module
ONEONEONE_CHILD = GenerationMode("111_child", produces_artifact=False,
                                 query_dependency_attributes=True)
ONEONEONE_CHILD.bazel_produced_artifact = types.MethodType(
    lambda self, pom_template_content: False, ONEONEONE_CHILD)


# these can be set explicitly in module metadata files
ALL_USER_MODES = (DYNAMIC, TEMPLATE, SKIP, DYNAMIC_ONEONEONE)

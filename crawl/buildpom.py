"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is responsible for parsing BUILD.pom and BUILD.pom.released files.
"""

from collections import namedtuple
from common import code
from common import mdfiles
from common import pomgenmode
from common import version
import os
import re
import sys

class MavenArtifactDef(object):
    """
    maven_artifact "targets" in BUILD.pom files are parsed into instances of
    this type. Information from BUILD.pom.released files is added, if that file
    exists.

    ==== Read out of the BUILD.pom file ====

    group_id: the maven artifact groupId of the bazel package.


    artifact_id: the maven artifact id (artifactId) of the bazel package.


    version: the maven artifact version of the bazel package.


    pom_generation_mode: the pom generation strategy, the type is
        common.pomgenmode.PomGenMode


    pom_template_file: if the pom_generation_mode is "template" (see above),
        this value has the template file name to use as pom template.


    include_deps: whether pomgen should include dependencies in the generated
        pom. This defaults to True, because figuring out dependencies and 
        including them in the generated pom is kinda the main purpose of 
        pomgen.  However, there are some edge cases where we just want a dummy 
        pom to facilitate upload to Nexus only (ie Beacon).
        Setting this to False also disables crawling source dependencies 
        referenced by this bazel package.
        

    ==== Read out of the optional BUILD.pom.released file ====

    version: the previously released version to Nexus

    artifact_hash: the hash of the artifact at the time it was previously 
                   released to Nexus


    ===== Internal attributes (never specified by the user) ====


    deps: additional targets this package depends on; list of Bazel labels.
        For example: deps = ["//projects/libs/servicelibs/srpc/srpc-thrift-svc-runtime"]

        Only used by tests.


    bazel_package: the bazel package the BUILD.pom file lives in 


    library_path: the path to the root directory of the library this
        monorepo package is part of


    requires_release: whether this monorepo package should be released (to Nexus
                      or local Maven repository)


    release_reason: the reason for releasing this artifact


    released_pom_content: if the file pom.xml.released exists next to the 
                          BUILD.pom file, the content of the pom.xml.released 
                          file
    =====

    Implementation notes:
        - properties are kept read-only whenever possible
        - the constructor provides default values for easier instantiation
          in test code

    """
    def __init__(self,
                 group_id,
                 artifact_id,
                 version,
                 pom_generation_mode=None,
                 pom_template_file=None,
                 deps=[],
                 include_deps=True,
                 released_version=None,
                 released_artifact_hash=None,
                 bazel_package=None,
                 library_path=None,
                 requires_release=None,
                 released_pom_content=None,
                 version_increment_strategy=None):
        self._group_id = group_id
        self._artifact_id = artifact_id
        self._version = version
        self._pom_generation_mode = pom_generation_mode
        self._pom_template_file = pom_template_file
        self._deps = deps
        self._include_deps = include_deps
        self._released_version = released_version
        self._released_artifact_hash = released_artifact_hash
        self._bazel_package = bazel_package
        self._library_path = library_path
        self._requires_release = requires_release
        self._release_reason = None
        self._released_pom_content = released_pom_content
        self._version_increment_strategy = version_increment_strategy

    @property
    def group_id(self):
        return self._group_id

    @property
    def artifact_id(self):
        return self._artifact_id

    @property
    def version(self):
        return self._version

    @property
    def pom_generation_mode(self):
        return self._pom_generation_mode

    @property
    def pom_template_file(self):
        return self._pom_template_file

    @property
    def deps(self):
        return self._deps

    @property
    def include_deps(self):
        return self._include_deps

    @property
    def released_version(self):
        return self._released_version

    @property
    def released_artifact_hash(self):
        return self._released_artifact_hash

    @released_artifact_hash.setter
    def released_artifact_hash(self, value):
        self._released_artifact_hash = value

    @property
    def bazel_package(self):
        return self._bazel_package

    @property
    def library_path(self):
        return self._library_path

    @library_path.setter
    def library_path(self, value):
        self._library_path = value

    @property
    def requires_release(self):
        if not self._pom_generation_mode.produces_artifact:
            # nothing ever to release
            return False
        return self._requires_release

    @requires_release.setter
    def requires_release(self, value):
        self._requires_release = value

    @property
    def release_reason(self):
        return self._release_reason

    @release_reason.setter
    def release_reason(self, value):
        self._release_reason = value

    @property
    def released_pom_content(self):
        return self._released_pom_content

    @property
    def version_increment_strategy(self):
        return self._version_increment_strategy

    def __str__(self):
        return "%s:%s" % (self._group_id, self._artifact_id)

    def __repr__(self):
        return str(self)

# only used internally for parsing
ReleasedMavenArtifactDef = namedtuple("ReleasedMavenArtifactDef", "version artifact_hash")

def maven_artifact(group_id=None,
                   artifact_id=None,
                   version=None,
                   pom_generation_mode=None,
                   pom_template_file=None,
                   include_deps=True,
                   deps=[]):
    """
    This function is only intended to be called from BUILD.pom files.    
    """
    return MavenArtifactDef(group_id,
                            artifact_id,
                            version,
                            pom_generation_mode,
                            pom_template_file,
                            deps,
                            include_deps)

def released_maven_artifact(version, artifact_hash):
    """
    This function is only intended to be called from BUILD.pom.released files.
    """
    return ReleasedMavenArtifactDef(version, artifact_hash)

def parse_maven_artifact_def(root_path, package):
    """
    Parses the BUILD.pom file *and* BUILD.pom.released file at the specified 
    path and returns a MavenArtifactDef instance.

    Returns None if there is no BUILD.pom file at the specified path.
    """
    content, path = mdfiles.read_file(root_path, package, mdfiles.BUILD_POM_FILE_NAME)
    if content is None:
        return None
    maven_artifact_func = code.get_function_block(content, "maven_artifact")
    try:
        art_def = eval(maven_artifact_func)
        pom_generation_mode = pomgenmode.from_string(art_def.pom_generation_mode)
    except:
        print("[ERROR] Cannot parse [%s]: %s" % (path, sys.exc_info()))
        raise

    if pom_generation_mode.produces_artifact:
        rel_art_def = _parse_released_maven_artifact_def(root_path, package)
        released_pom_content = _read_released_pom(root_path, package)

        vers_incr_strat = version.get_version_increment_strategy(content, path)

        return _augment_art_def_values(art_def, rel_art_def, package,
                                       released_pom_content,
                                       vers_incr_strat,
                                       pom_generation_mode)
    else:
        return _augment_art_def_values(art_def, 
                                       user_rel_art_def=None, 
                                       bazel_package=package,
                                       released_pom_content=None,
                                       version_increment_strategy=None,
                                       pom_generation_mode=pom_generation_mode)

def _read_released_pom(root_path, package):
    content, _ = mdfiles.read_file(root_path, package, mdfiles.POM_XML_RELEASED_FILE_NAME)
    return content

def _parse_released_maven_artifact_def(root_path, package):
    """
    Parses the BUILD.pom.released file at the specified path and returns a 
    MavenArtifactDef instance.

    Returns None if there is no BUILD.pom.released file at the specified path.
    """
    content, path = mdfiles.read_file(root_path, package, mdfiles.BUILD_POM_RELEASED_FILE_NAME)
    if content is None:
        return None
    try:
        return eval(content)
    except:
        print("[ERROR] Cannot parse [%s]: %s" % (path, sys.exc_info()))
        raise

def _augment_art_def_values(user_art_def, user_rel_art_def, bazel_package,
                            released_pom_content, version_increment_strategy,
                            pom_generation_mode):
    """
    Defaults values that have not been provided in the BUILD.pom file.

    Args:
        user_art_def: the MavenArtifactDef instance from the BUILD.pom file

        user_rel_art_def: the ReleasedMavenArtifactDef instance from the 
            BUILD.pom.released file, may be None

        bazel_package: the bazel package the parsed BUILD.pom file lives in

        released_pom_content: the content of the pom.xml.released file, may
            be None

        version_increment_strategy: the artifacts version increment strategy,
            as specified in the BUILD.pom file, may be None

        pom_generation_mode: the strongly typed pom_generation_mode 
            (common.pomgenmode.PomGenMode)
    """
    return MavenArtifactDef(
        user_art_def.group_id,
        user_art_def.artifact_id,
        user_art_def.version,
        pom_generation_mode,
        user_art_def.pom_template_file,
        user_art_def.deps,
        True if user_art_def.include_deps is None else user_art_def.include_deps,
        user_rel_art_def.version if user_rel_art_def is not None else None,
        user_rel_art_def.artifact_hash if user_rel_art_def is not None else None,
        bazel_package,
        released_pom_content=released_pom_content,
        version_increment_strategy=version_increment_strategy)

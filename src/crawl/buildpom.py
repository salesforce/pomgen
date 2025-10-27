"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module is responsible for parsing BUILD.pom and BUILD.pom.released files.
"""

import collections
import common.code as code
import common.common as common
import common.mdfiles as mdfiles
import common.genmode as genmode
import os


class MavenArtifactDef:
    """
    Represents an instance of a maven_artifact rule defined in a BUILD.pom file.
    Information from the BUILD.pom.released file is added, if that file exists.


    ==== Read out of the metadata (for ex BUILD.pom) file ====

    group_id: the maven artifact groupId of the bazel package.

    artifact_id: the maven artifact id (artifactId) of the bazel package.

    version: the maven artifact version of the bazel package.

    generation_mode: the generation strategy, the type is
        common.genmode.GenerationMode

    custom_pom_template: if the generation_mode is "template",
        this is the content of the specified template file

    include_deps: whether pomgen should include dependencies in the generated
        pom. This defaults to True, because figuring out dependencies and 
        including them in the generated pom is kinda the main purpose of 
        pomgen.  However, there are some edge cases where we just want a dummy 
        pom to facilitate upload to Nexus only.
        Setting this to False also disables crawling source dependencies 
        referenced by this bazel package.

    change_detection: whether pomgen should mark this artifact as needing to be
        released based on whether changes have been made made to the artifact
        since it was last released.  Defaults to True.
        If set explicitly to False, then the artifact is unconditionally marked
        as needing to be released.

    additional_change_detected_packages: list of additional bazel packages
        pomgen should check for changes when determining whether this artifact
        needs to be released.

    gen_dependency_management_pom: whether to generate an additional pom.xml
       that only contains <dependencyManagement>. Defaults to False.

    jar_path: optional and for supporting the edge-case when the jar artifact
        already exists: if set, the relative path from this BUILD.pom file to
        the jar artifact to use. this can be used if bazel doesn't actually
        build the jar (-> java_import).

    version_increment_strategy_name: specifies how this artifacts version should
        be incremented.

    1_1_1_mode: whether this artifact is in 1:1:1 mode: all bazel subpackages
                of this bazel package use genmode.SKIP

    emitted_dependencies: specifies extra dependencies to include, or exclude,
        in the generated manifest. Use manifest-native syntax, and prefix with
        '-' to exclude.

    excluded_dependency_paths: for source dependencies of this artifact,
        a list of paths or path prefixes, to not crawl, relative to the package
        of this artifact.
        These dependencices will not end up in the generated manifest file.
        Note that there is also a global configuration setting with the same
        name that applies to all crawled source dependencies.


    ==== Read out of the optional released md file (for ex BUILD.pom.released)

    released_version: the previously released version to Nexus.

    released_artifact_hash: the hash of the artifact at the time it was 
        previously released to Nexus.


    ===== Internal attributes (never specified by the user in config/md files)

    deps: additional targets this package depends on; list of Bazel labels.
        For example: deps = ["//projects/libs/srpc/srpc-thrift-svc-runtime"]
        The deps attribute is typically only used by tests, that's why it is
        listed here under "internal attributes", although it is specified in the
        BUILD.pom file.

    bazel_package: the bazel package (relative path to the directory) where the 
        manifest file (for ex MVN-INF/) directory and the build file live.
        The build file is not guaranteed to exist.

    bazel_target: the bazel target that builds the binary artifact.

    library_path: the path to the root directory of the library this artifact
        is part of.

    requires_release: whether this artifact should be released (to Nexus
        or local Maven repository).

    release_reason: the reason for releasing this artifact.

    released_pom_content: if the file pom.xml.released exists next to the 
        BUILD.pom file, the content of the pom.xml.released file.

    generation_strategy: the generation strategy for this artfifact.

    parent_artifact_def: for 111 child packages only, the parent package
        the has the module manifest
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
                 generation_mode=genmode.DYNAMIC,
                 custom_pom_template_content=None,
                 include_deps=True,
                 change_detection=True,
                 additional_change_detected_packages=[],
                 gen_dependency_management_pom=False,
                 jar_path=None,
                 deps=[],
                 version_increment_strategy_name=None,
                 released_version=None,
                 released_artifact_hash=None,
                 bazel_package=None,
                 bazel_target=None,
                 library_path=None,
                 requires_release=None,
                 released_pom_content=None,
                 generation_strategy=None,
                 parent_artifact_def=None,
                 excluded_dependency_paths=[],
                 emitted_dependencies=[],
                 attr_name_to_md_file_path=None):
        self._group_id = group_id
        self._artifact_id = artifact_id
        self._version = version
        self._generation_mode = generation_mode
        self._custom_pom_template_content = custom_pom_template_content
        self._include_deps = include_deps
        self._change_detection = change_detection
        self._additional_change_detected_packages = additional_change_detected_packages
        self._gen_dependency_management_pom = gen_dependency_management_pom
        self._jar_path = jar_path
        self._deps = deps
        self._version_increment_strategy_name = version_increment_strategy_name
        self._released_version = released_version
        self._released_artifact_hash = released_artifact_hash
        self._bazel_package = bazel_package
        self._bazel_target = bazel_target
        self._library_path = library_path
        self._requires_release = requires_release
        self._release_reason = None
        self._released_pom_content = released_pom_content
        self._generation_strategy = generation_strategy
        self._parent_artifact_def = parent_artifact_def
        self._excluded_dependency_paths = excluded_dependency_paths
        self._emitted_dependencies = emitted_dependencies
        self._attr_name_to_md_file_path = {} if attr_name_to_md_file_path is None else attr_name_to_md_file_path

        # data cleanup/verification/sanitization
        # these are separate methods for better readability
        self._sanitize_additional_change_detected_packages()


    @property
    def group_id(self):
        return self._group_id

    @group_id.setter
    def group_id(self, value):
        self._group_id = value

    @property
    def artifact_id(self):
        return self._artifact_id

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value

    @property
    def generation_mode(self):
        return self._generation_mode

    @property
    def custom_pom_template_content(self):
        return self._custom_pom_template_content

    @custom_pom_template_content.setter
    def custom_pom_template_content(self, value):
        self._custom_pom_template_content = value

    @property
    def include_deps(self):
        return self._include_deps

    @property
    def change_detection(self):
        return self._change_detection

    @property
    def additional_change_detected_packages(self):
        return self._additional_change_detected_packages

    @property
    def gen_dependency_management_pom(self):
        return self._gen_dependency_management_pom

    @property
    def jar_path(self):
        return self._jar_path

    @property
    def deps(self):
        return self._deps

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
    def bazel_target(self):
        return self._bazel_target

    @property
    def library_path(self):
        return self._library_path

    @library_path.setter
    def library_path(self, value):
        self._library_path = value

    @property
    def requires_release(self):
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
    def emitted_dependencies(self):
        return self._emitted_dependencies

    @property
    def version_increment_strategy_name(self):
        return self._version_increment_strategy_name

    @property
    def generation_strategy(self):
        return self._generation_strategy

    @property
    def parent_artifact_def(self):
        return self._parent_artifact_def

    @property
    def excluded_dependency_paths(self):
        return self._excluded_dependency_paths

    def get_md_file_path_for_attr(self, attr_name):
        """
        Returns the relative path, from the repository root, of
        the metadata file the given attribute was read from.
        Raises if the given attribute name is not known.
        """
        return self._attr_name_to_md_file_path[attr_name]

    def register_md_file_path_for_attr(self, attr_name, md_rel_path):
        """
        Args:
            md_rel_path: the relative path to the md file, starting at the repository root.
        """
        assert attr_name not in self._attr_name_to_md_file_path
        assert md_rel_path is not None
        self._attr_name_to_md_file_path[attr_name] = md_rel_path

    def is_or_has_same_111_parent(self, other):
        """
        For a child 111 package artifact def, returns True if either:
        - the given artifact def is this artifact def's 111 parent or
        - the given artifact def has the same 111 parent as this artifact def
        """
        assert self.generation_mode is genmode.ONEONEONE_CHILD
        assert self.parent_artifact_def is not None
        assert isinstance(other, MavenArtifactDef)
        if other.generation_mode is genmode.DYNAMIC_ONEONEONE:
            return self.parent_artifact_def is other
        elif other.generation_mode is genmode.ONEONEONE_CHILD:
            return self.parent_artifact_def is other.parent_artifact_def
        return False

    def __str__(self):
        return "Metadata@%s" % self.bazel_package

    def __repr__(self):
        return str(self)

    def _sanitize_additional_change_detected_packages(self):
        # we treat these bazel package as paths relative to the repo root,
        # so make sure they don't start with "//"
        self._additional_change_detected_packages = [p[2:] if p.startswith("//") else p for p in self._additional_change_detected_packages]


# only used internally for parsing
ReleasedMavenArtifactDef = collections.namedtuple("ReleasedMavenArtifactDef", "version artifact_hash")


def parse_maven_artifact_def(root_path, package, generation_strategy):
    """
    Parses the metadata (for ex BUILD.pom) file *and* the released metadata
    file (for ex BUILD.pom.released) file at the specified package and returns a
    MavenArtifactDef instance.

    Returns None if there is no metadata (for ex BUILD.pom) file at the
    specified path.
    """
    package_md_path = os.path.join(package, generation_strategy.metadata_path)
    content = common.read_file(os.path.join(root_path, package_md_path), must_exist=False)
    if content is None:
        return None
    ma_attrs, _ = code.parse_artifact_attributes(content)
    art_def = MavenArtifactDef(
        group_id=ma_attrs.get("group_id", None),
        artifact_id=ma_attrs.get("artifact_id", None),
        version=ma_attrs.get("version", None),
        # pom_generation_mode can be removed, we still look for it for now
        # to make the transition to the new name (generation_mode) easier
        generation_mode=ma_attrs.get(
            "generation_mode", ma_attrs.get("pom_generation_mode")),
        include_deps=ma_attrs.get("include_deps", True),
        change_detection=ma_attrs.get("change_detection", True),
        additional_change_detected_packages=ma_attrs.get("additional_change_detected_packages", []),
        gen_dependency_management_pom=ma_attrs.get("generate_dependency_management_pom", False),
        jar_path=ma_attrs.get("jar_path", None),
        bazel_target=ma_attrs.get("target_name", None),
        deps=ma_attrs.get("deps", []),
        generation_strategy=generation_strategy,
        excluded_dependency_paths=ma_attrs.get("excluded_dependency_paths", []),
        emitted_dependencies=ma_attrs.get("emitted_dependencies", []),
    )

    for attr_name in ma_attrs.keys():
        art_def.register_md_file_path_for_attr(attr_name, package_md_path)
    

    md_dir_name = os.path.dirname(generation_strategy.metadata_path)        
    template_path = ma_attrs.get("pom_template_file", None)
    if template_path is not None:
        template_path = os.path.join(md_dir_name, template_path)
        template_content, _ = mdfiles.read_file(root_path, package, template_path, must_exist=True)
        art_def.custom_pom_template_content = template_content
    
    generation_mode = genmode.from_string(art_def.generation_mode)

    if generation_mode.produces_artifact:
        rel_art_def, md_file_path = _parse_released_artifact_def(root_path, package, generation_strategy)
        released_pom_content = _read_released_manifest(root_path, package, generation_strategy)

        vers_inc_strat_name = ma_attrs.get("version_increment_strategy", None)
        art_def = _augment_art_def_values(art_def, rel_art_def, package,
                                       md_dir_name,
                                       released_pom_content,
                                       vers_inc_strat_name,
                                       generation_mode)
        if art_def.released_version is not None:
            art_def.register_md_file_path_for_attr("released_version", md_file_path)
        if art_def.released_artifact_hash is not None:
            art_def.register_md_file_path_for_attr("released_artifact_hash", md_file_path)
        return art_def
    else:
        return _augment_art_def_values(art_def, 
                                       rel_art_def=None,
                                       bazel_package=package,
                                       md_dir_name=md_dir_name,
                                       released_pom_content=None,
                                       version_increment_strategy_name=None,
                                       generation_mode=generation_mode)


def _read_released_manifest(root_path, package, generation_strategy):
    """
    For example pom.xml.released
    """
    content, _ = mdfiles.read_file(root_path, package, generation_strategy.released_manifest_path)
    return content


def _parse_released_artifact_def(root_path, package, generation_strategy):
    """
    Parses the released metadata file at the specified path and returns a tuple of
    (ReleasedMavenArtifactDef instance, rel path from root to md file)

    Returns (None, None) if there is no released metadata file at the specified path.
    """
    content, abs_path = mdfiles.read_file(root_path, package, generation_strategy.released_metadata_path)
    if content is None:
        return None, None
    attrs, _ = code.parse_attributes(content)
    return ReleasedMavenArtifactDef(
        version=attrs.get("version", None),
        artifact_hash=attrs.get("artifact_hash", None)), os.path.relpath(abs_path, root_path)
    

def _augment_art_def_values(user_art_def, rel_art_def, bazel_package,
                            md_dir_name,
                            released_pom_content,
                            version_increment_strategy_name,
                            generation_mode):
    """
    Defaults values that have not been provided explicitly.
    """
    return MavenArtifactDef(
        group_id=user_art_def.group_id,
        artifact_id=user_art_def.artifact_id,
        version=user_art_def.version,
        generation_mode=generation_mode,
        custom_pom_template_content=user_art_def.custom_pom_template_content,
        include_deps=True if user_art_def.include_deps is None else user_art_def.include_deps,
        change_detection=True if user_art_def.change_detection is None else user_art_def.change_detection,
        additional_change_detected_packages=[] if user_art_def.additional_change_detected_packages is None else user_art_def.additional_change_detected_packages,
        gen_dependency_management_pom=False if user_art_def.gen_dependency_management_pom is None else user_art_def.gen_dependency_management_pom,
        jar_path=None if user_art_def.jar_path is None else os.path.normpath(os.path.join(bazel_package, md_dir_name, user_art_def.jar_path)),
        deps=user_art_def.deps,
        bazel_target=user_art_def.bazel_target if user_art_def.bazel_target is not None else os.path.basename(bazel_package),
        released_version=rel_art_def.version if rel_art_def is not None else None,
        released_artifact_hash=rel_art_def.artifact_hash if rel_art_def is not None else None,
        bazel_package=bazel_package,
        released_pom_content=released_pom_content,
        version_increment_strategy_name=version_increment_strategy_name,
        generation_strategy=user_art_def.generation_strategy,
        excluded_dependency_paths=user_art_def.excluded_dependency_paths,
        emitted_dependencies=user_art_def.emitted_dependencies,
        attr_name_to_md_file_path=user_art_def._attr_name_to_md_file_path,
    )

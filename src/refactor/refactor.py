"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import argparse
import collections
import common.argsupport as argsupport
import common.code as code
import common.common as common
import common.manifestcontent as manifestcontent
import common.mdfiles as mdfiles
import config.config as config
import generate.generationstrategyfactory as generationstrategyfactory
import crawl.workspace as workspace
import os
import sys


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Popeye Refactor Recipes")
    parser.add_argument("--package", type=str, required=True,
        help="Updates metadata files under the specified package(s). " + argsupport.get_package_doc())
    parser.add_argument("--pull_common_attrs", required=False, action="store_true",
        help="Move common attributes from the module metadata file into the library metadata file")
    parser.add_argument("--with_spinach", required=False, action="store_true",
        help="Makes the refactoring extra strong")
    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")
    parser.add_argument("--repo_root", type=str, required=False,
        help="the root of the repository")    
    return parser.parse_args(args)


def main(args):
    repository_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repository_root)
    fac = generationstrategyfactory.GenerationStrategyFactory(
        repository_root, cfg, manifestcontent.NOOP, verbose=args.verbose)
    ws = workspace.Workspace(repository_root, cfg, fac, cache_artifact_defs=False)
    packages = argsupport.get_all_packages(repository_root, args.package, fac, verbose=args.verbose)
    assert len(packages) > 0, "Did not find any packages at [%s]" % args.package

    if args.pull_common_attrs:
        lib_to_art = collections.defaultdict(list)
        for package in packages:
            art_def = ws.parse_maven_artifact_def(package)
            lib_to_art[art_def.library_path].append(art_def)
        for lib_path in lib_to_art:
            art_defs = lib_to_art[lib_path]
            if len(art_defs) > 1:
                group_id = _rm_attr_from_artifacts(repository_root, "group_id", art_defs)
                version = _rm_attr_from_artifacts(repository_root, "version", art_defs)
                version_incr_strat = _rm_attr_from_artifacts(repository_root, "version_increment_strategy", art_defs)

                md_dir_name = os.path.dirname(art_defs[0].generation_strategy.metadata_path)
                lib_md_file_rel_path = os.path.join(lib_path, md_dir_name, mdfiles.LIB_ROOT_FILE_NAME)
                abs_path = os.path.join(repository_root, lib_md_file_rel_path)
                content = common.read_file(abs_path).strip()
                if len(content) == 0:
                    content = _get_library_content(version, version_incr_strat, group_id)
                    common.write_file(abs_path, content)
                else:
                    # if for some reason the lib file has some content already
                    # we don't update it
                    pass


def _rm_attr_from_artifacts(repository_root, attr_name, artifact_definitions):
    value = None
    for art_def in artifact_definitions:
        if value is None:
            value = getattr(art_def, attr_name)
        if value is not None:
            assert value == getattr(art_def, attr_name),\
                "inconsistent value in artifact metadata %s for attr %s, expected %s" % (str(art_def), attr_name, value)
            _rm_attr(repository_root, art_def, attr_name)
    return value


def _rm_attr(repository_root, artifact_definition, attr_name):
    md_path = artifact_definition.get_md_file_path_for_attr(attr_name)
    if not md_path.endswith(mdfiles.LIB_ROOT_FILE_NAME):
        abs_path = os.path.join(repository_root, md_path)
        content = common.read_file(abs_path)
        _, value_indexes = code.parse_artifact_attributes(content)
        start, end = value_indexes[attr_name]
        if attr_name == "version_increment_strategy":
            # we remove the entire artifact_update rule
            start = content.find("maven_artifact_update(")
            if start == -1:
                start = content.index("artifact_update(")
            start = _index_of_prev_linebreak(content, start)
            end = content.index(")", end)
        else:
            start = _index_of_prev_linebreak(content, start)
            end = _index_of_next_attr_sep(content, end)
        updated_content = content[:start] + content[end+1:]
        common.write_file(abs_path, updated_content)


def _index_of_prev_linebreak(content, start_index):
    for i in range(start_index, 0, -1):
        if content[i] == "\n":
            return i
    assert False


def _index_of_next_attr_sep(content, start_index):
    for i in range(start_index, len(content)):
        if content[i] == "\n":
            return i-1
    return i


def _get_library_content(version, version_increment_strategy, group_id=None):
    assert version is not None
    assert version_increment_strategy is not None
    content = """artifact(
%s
)

artifact_update(
    version_increment_strategy = "%s",
)
"""
    attrs = ""
    if group_id is not None:
        attrs = "    group_id = \"%s\",\n" % group_id
    attrs += "    version = \"%s\"," % version
    return content % (attrs, version_increment_strategy)


if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    main(args)

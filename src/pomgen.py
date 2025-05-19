"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


The pomgen cmdline entry-point.
"""

from common import argsupport
from common import common
from common import logger
from common import maveninstallinfo
from common import overridefileinfo
from common import mdfiles
from config import config
from crawl import bazel
from crawl import crawler as crawlerm
from crawl import dependencymd as dependencym
from crawl import libaggregator
from crawl import pom
from crawl import pomcontent as pomcontentm
from crawl import workspace
import argparse
import os
import sys


def main(args):
    args = _parse_arguments(args)

    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root, args.verbose)
    pom_content = pomcontentm.PomContent()
    dependencymd = dependencym.DependencyMetadata(cfg.jar_artifact_classifier)
    if args.pom_description is not None:
        pom_content.description = args.pom_description
    if args.verbose:
        logger.debug("Global pom content: %s" % pom_content)

    override_file_info = overridefileinfo.OverrideFileInfo(cfg.override_file_paths, repo_root)
    mvn_install_info = maveninstallinfo.MavenInstallInfo(cfg.maven_install_paths)
    ws = workspace.Workspace(repo_root, cfg,
                             mvn_install_info,
                             pom_content,
                             dependencymd,
                             override_file_info.label_to_overridden_fq_label,
                             verbose=args.verbose)
    packages = argsupport.get_all_packages(repo_root, args.package)
    packages = ws.filter_artifact_producing_packages(packages)
    if len(packages) == 0:
        raise Exception("Did not find any artifact producing BUILD.pom packages at [%s]" % args.package)
    crawler = crawlerm.Crawler(ws, cfg.pom_template, args.verbose)
    result = crawler.crawl(packages, follow_references=not args.ignore_references, force_release=args.force)

    if len(result.artifact_generation_contexts) == 0:
        logger.info("No releases are required. pomgen will not generate any pom files. To force pom generation, use pomgen's --force option.")
    else:
        output_dir = _get_output_dir(args)

        lib_paths = bazel.query_all_libraries(repo_root, packages)
        if args.write_libraries_hint_file:
            if not args.ignore_references:
                # the libraries hint file contains the list of all upstream
                # libs (including the current lib) - this only works when
                # crawling is enabled (ignore_references disables crawling)
                if len(lib_paths) == 1:
                    # a single lib as a starting point is the common case,
                    # so we do not bother with the other cases for now
                    path = lib_paths[0]
                    _write_all_libraries_hint_files(result, output_dir, path)

        # hardcoded to pom.xml files right here, but in the future pluggable?
        pomgens = [ctx.generator for ctx in result.artifact_generation_contexts]

        for pomgen in pomgens:
            pom_dest_dir = os.path.join(output_dir, pomgen.bazel_package)
            if not os.path.exists(pom_dest_dir):
                os.makedirs(pom_dest_dir)

            # the goldfile pom is actually a pomgen metadata file, so we 
            # write it using the mdfiles module, which ensures it goes 
            # into the proper location within the specified bazel package
            if args.pom_goldfile:
                pom_content = pomgen.gen(pom.PomContentType.GOLDFILE)
                pom_goldfile_path = mdfiles.write_file(pom_content, output_dir, pomgen.bazel_package, mdfiles.POM_XML_RELEASED_FILE_NAME)
                logger.info("Wrote pom goldfile to [%s]" % pom_goldfile_path)
            else:
                pom_content = pomgen.gen(pom.PomContentType.RELEASE)
                pom_path = os.path.join(
                    pom_dest_dir, "%s.xml" % cfg.pom_base_filename)
                _write_file(pom_path, pom_content)
                logger.info("Wrote pom file to [%s]" % pom_path)
                for i, companion_pomgen in enumerate(pomgen.get_companion_generators()):
                    pom_content = companion_pomgen.gen(pom.PomContentType.RELEASE)
                    pom_path = os.path.join(pom_dest_dir, 
                        "%s_companion%s.xml" % (cfg.pom_base_filename, i))
                    _write_file(pom_path, pom_content)
                    logger.info("Wrote companion pom file to [%s]" % pom_path)

                # if jar_path has been set in the BUILD.pom file, we write a
                # hint file with the path out so we can find it more easily
                # later when jars are processed
                jar_path = pomgen.artifact_def.jar_path
                if jar_path is not None:
                    hint_file_path = os.path.join(pom_dest_dir, mdfiles.JAR_LOCATION_HINT_FILE)
                    _write_file(hint_file_path, jar_path)
                    logger.info("Wrote jar location hint file [%s] with content [%s]" % (hint_file_path, jar_path))



def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Monorepo Pom Generator")
    parser.add_argument("--package", type=str, required=True,
        help="Narrows pomgen to the specified package(s). " + argsupport.get_package_doc())
    parser.add_argument("--destdir", type=str, required=True,
        help="The root directory generated poms are written to")
    parser.add_argument("--repo_root", type=str, required=False,
        help="The root of the repository")
    parser.add_argument("--force", required=False, action="store_true",
        help="If set, always generated poms, regardless of whether an artifact has changed since it was last released")
    parser.add_argument("--ignore_references", required=False, action="store_true",
        help="If set, pomgen does not follow references in BUILD files and only processes the packages packages specified by --package (instead of using them as a starting point and then crawling BUILD files)")
    parser.add_argument("--pom_goldfile", required=False, action="store_true",
        help="Generates a goldfile pom")
    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")
    parser.add_argument("--pom.description", type=str, required=False,
        dest="pom_description", help="Written as the pom's <description/>")
    parser.add_argument("--write_libraries_hint_file", required=False, action="store_true",
        help="The libraries hint file is used by the wrapper script in //maven, it is not needed when running pomgen directly")

    return parser.parse_args(args)


def _write_file(path, content):                    
    with open(path, "w") as f:
        f.write(content)


def _get_output_dir(args):
    if not args.destdir:
        return None
    destdir = args.destdir
    if os.path.isabs(destdir):
        destdir = os.path.realpath(args.destdir)
    else:
        # resolve relative to workspace
        ws = os.getenv("BUILD_WORKSPACE_DIRECTORY")
        assert ws is not None, "not using bazel run"
        destdir = os.path.join(ws, destdir)
    if os.path.exists(destdir):
        if not os.path.isdir(destdir):
            raise Exception("[%s] is not a directory" % destdir)
    else:
        os.makedirs(destdir)
    return destdir


def _write_all_libraries_hint_files(crawler_result, output_dir, start_lib_path):
    libaggregator.get_libraries_to_release(crawler_result.nodes)
    lib_paths = [lib.library_path for lib in libaggregator.LibraryNode.ALL_LIBRARY_NODES if lib.requires_release]
    if len(lib_paths) > 0:
        hint_file_dir = os.path.join(output_dir, start_lib_path)
        if not os.path.exists(hint_file_dir):
            os.makedirs(hint_file_dir)
        hint_file_path = os.path.join(hint_file_dir, "libraries.txt")
        _write_file(hint_file_path, "\n".join(
            ["# the root lib path, followed by the paths to its upstream dependencies"] + lib_paths))
        logger.info("Wrote libraries hint file to [%s]" % hint_file_path)


if __name__ == "__main__":
    main(sys.argv[1:])

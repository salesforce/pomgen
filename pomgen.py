#!/usr/bin/env python

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
from common import mdfiles
from config import config
from crawl import crawler
from crawl import pom
from crawl import pomcontent as pomcontentm
from crawl import workspace
import argparse
import os
import re
import sys


def _write_file(path, content):                    
    with open(path, "w") as f:
        f.write(content)


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Monorepo Pom Generator")
    parser.add_argument("--package", type=str, required=True,
        help="Narrows pomgen to the specified package(s). " + argsupport.get_package_doc())
    parser.add_argument("--destdir", type=str, required=True,
        help="The root directory generated poms are written to")
    parser.add_argument("--repo_root", type=str, required=False,
        help="The root of the repository")
    parser.add_argument("--recursive", required=False, action='store_true',
        help="Also generate poms for dependencies, disabled by default")
    parser.add_argument("--force", required=False, action='store_true',
        help="If set, always generated poms, regardless of whether an artifact has changed since it was last released")
    parser.add_argument("--pom_goldfile", required=False, action='store_true',
        help="Generates a goldfile pom")
    parser.add_argument("--verbose", required=False, action='store_true',
        help="Verbose output")
    parser.add_argument("--pom.description", type=str, required=False,
        dest="pom_description", help="Written as the pom's <description/>")
    return parser.parse_args(args)


def _get_output_dir(args):
    if not args.destdir:
        return None
    if not os.path.exists(args.destdir):
        os.makedirs(args.destdir)
    if not os.path.isdir(args.destdir):
        raise Exception("[%s] is not a directory %s" % args.out)
    destdir = os.path.realpath(args.destdir)
    logger.info("Output dir [%s]" %  destdir)
    return destdir


def main(args):
    args = _parse_arguments(args)
    repo_root = common.get_repo_root(args.repo_root)
    cfg = config.load(repo_root, args.verbose)
    pom_content = pomcontentm.PomContent()
    if args.pom_description is not None:
        pom_content.description = args.pom_description
    if args.verbose:
        logger.debug("Global pom content: %s" % pom_content)

    mvn_install_info = maveninstallinfo.MavenInstallInfo(cfg.maven_install_paths)
    ws = workspace.Workspace(repo_root,
                             cfg.excluded_dependency_paths,
                             cfg.all_src_exclusions,
                             mvn_install_info,
                             pom_content)
    packages = argsupport.get_all_packages(repo_root, args.package)
    packages = ws.filter_artifact_producing_packages(packages)
    if len(packages) == 0:
        raise Exception("Did not find any artifact producing BUILD.pom packages at [%s]" % args.package)
    spider = crawler.Crawler(ws, cfg.pom_template, args.verbose)
    result = spider.crawl(packages,
                          follow_monorepo_references=args.recursive,
                          force_release=args.force)

    if len(result.pomgens) == 0:
        logger.info("No releases are required. pomgen will not generate any pom files. To force pom generation, use pomgen's --force option.")
    else:
        output_dir = _get_output_dir(args)

        for pomgen in result.pomgens:
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
                pom_path = os.path.join(pom_dest_dir, "pom.xml")
                _write_file(pom_path, pom_content)
                logger.info("Wrote pom file to [%s]" % pom_path)
                for i, companion_pomgen in enumerate(pomgen.get_companion_generators()):
                    pom_content = companion_pomgen.gen(pom.PomContentType.RELEASE)
                    pom_path = os.path.join(pom_dest_dir, "pom_companion%s.xml" % i)
                    _write_file(pom_path, pom_content)
                    logger.info("Wrote companion pom file to [%s]" % pom_path)

if __name__ == "__main__":
    main(sys.argv[1:])

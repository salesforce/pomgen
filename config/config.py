"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Responsible for loading a config file of the following format:

[general]
# Path to the pom template, used when generating pom.xml files for jar artifacts
pom_template_path=
# Path to the file(s) that lists external dependencies - multiple files are 
# supported, comma-separated.
external_dependencies_path=

[crawler]
# A list of path prefixes that are not crawled by pomgen.  Any dependency
# that starts with one of the strings returned by this method is skipped 
# and not processed (and not included in the generated pom.xml).
# These dependencies are similar to Maven's "provided" scope: if they are
# needed at runtime, it is expected that the final runtime assembly
# contains them.
excluded_dependency_paths=projects/protos/,

[artifact]
# Paths not considered when determining whether an artifact has changed
excluded_relative_paths=src/tests,

# File names not considered when determining whether an artifact has changed
excluded_filenames=.gitignore,

# Ignored file extensions when determining whether an artifact has changed
excluded_extensions=.md,

# query versioning mode for proposed next versions
versioning_mode=semver
"""

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from . import exclusions
import os
from common import logger


def load(repo_root, verbose=False):
    """
    Looks for a config file called .pomgenrc in the following locations:
      - <repo_root>/.pomgenrc

    If no config file is found, uses default values.

    Returns a Config instance.
    """
    parser = configparser.RawConfigParser()

    def gen(option, dflt):
        """Read from [general] section """
        return _get_value_with_default(parser, "general", option, dflt)

    def crawl(option, dflt):
        """Read from [crawler] section """
        return _get_value_with_default(parser, "crawler", option, dflt)

    def artifact(option, dflt):
        """Read from [artifact] section """
        return _get_value_with_default(parser, "artifact", option, dflt)

    cfg_path = os.path.join(repo_root, ".pomgenrc")
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            parser.readfp(f)

    pom_template_p = gen("pom_template_path", ["config/pom_template.xml"])
    external_deps_p=gen("external_dependencies_path", ["WORKSPACE"])

    cfg = Config(
        pom_template_path_and_content=_read_files(repo_root, pom_template_p)[0],
        external_deps_path_and_content=_read_files(repo_root, external_deps_p),
        excluded_dependency_paths=crawl("excluded_dependency_paths", ()),
        excluded_src_relpaths=artifact("excluded_relative_paths", ("src/test",)),
        excluded_src_file_names=artifact("excluded_filenames", (".gitignore",)),
        excluded_src_file_extensions=artifact("excluded_extensions", (".md",)),
        versioning_mode=artifact("versioning_mode", "semver"),
    )

    if verbose:
        logger.raw("Running with configuration:\n%s\n" % str(cfg))

    return cfg


def _get_value_with_default(parser, section, option, dflt):
    try:
        return parser.get(section, option)
    except configparser.NoOptionError:
        return dflt
    except configparser.NoSectionError:
        return dflt


class Config:

    def __init__(self, 
                 pom_template_path_and_content=("",""),
                 external_deps_path_and_content=[],
                 excluded_dependency_paths=(),
                 excluded_src_relpaths=(),
                 excluded_src_file_names=(),
                 excluded_src_file_extensions=(),
                 versioning_mode="semver"):

        # general
        self.pom_template_path_and_content=pom_template_path_and_content
        self.external_deps_path_and_content = external_deps_path_and_content

        # crawler
        self.excluded_dependency_paths = _add_pathsep(_to_tuple(excluded_dependency_paths))

        # artifact
        self.excluded_src_relpaths = _add_pathsep(_to_tuple(excluded_src_relpaths))
        self.excluded_src_file_names = _to_tuple(excluded_src_file_names)
        self.excluded_src_file_extensions = _to_tuple(excluded_src_file_extensions)
        self.versioning_mode = versioning_mode

    @property
    def pom_template(self):
        return self.pom_template_path_and_content[1]

    @property
    def external_dependencies(self):
        # we'll just append the content of each file here
        all_content = ""
        for path,content in self.external_deps_path_and_content:
            all_content += content + "\n"
        return all_content

    @property
    def all_src_exclusions(self):
        """
        Convenience method that returns a named tuple of all source exclusions.
        """
        return exclusions.src_exclusions(self.excluded_src_relpaths,
                                         self.excluded_src_file_names,
                                         self.excluded_src_file_extensions)

    def __str__(self):
        return """[general]
pom_template_path=%s
external_dependencies_path=%s

[crawler]
excluded_dependency_paths=%s

[artifact]
excluded_relative_paths=%s
excluded_filenames=%s
excluded_extensions=%s
versioning_mode=%s
""" % (self.pom_template_path_and_content[0],
       ",".join([t[0] for t in self.external_deps_path_and_content]),
       self.excluded_dependency_paths,
       self.excluded_src_relpaths,
       self.excluded_src_file_names,
       self.excluded_src_file_extensions,
       self.versioning_mode)

def _to_tuple(thing):
    if isinstance(thing, tuple):
        return thing
    elif isinstance(thing, list):
        return tuple(thing)
    elif isinstance(thing, str):
        tokens = thing.split(",")
        filtered_tokens = [t.strip() for t in tokens if len(t.strip()) > 0]
        return tuple(filtered_tokens)
    raise Exception("Cannot convert to tuple")

def _read_files(repo_root, paths):
    """
    Returns a list of tuples: (<path>, <file content>).
    """
    paths = _to_tuple(paths)
    path_and_content = []
    for path in paths:
        with open(os.path.join(repo_root, path), "r") as f:
            path_and_content.append((path, f.read().strip()))
    return path_and_content

def _add_pathsep(paths):
    return tuple([p if p.endswith(os.sep) else p+os.sep for p in paths])

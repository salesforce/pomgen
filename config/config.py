"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Responsible for loading a config file of the following format:

[general]
# Path to the pom template, used when generating pom.xml files for jar artifacts
pom_template_path=
# A list of paths to pinned maven_install json files.
# Globs are supported, for example: tools/maven_install/*.json
maven_install_paths=maven_install.json,

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
transitives_versioning_mode=semver|counter

# The classifier used for all jars artifacts assembled by pomgen
# By default, no classifier is set
# The same value can also be specified by setting the environment variable
# POMGEN_JAR_CLASSIFIER - the environment variable takes precedence over the
# value set in this cfg file
jar_classifier=javax
"""

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from config import exclusions
from common import logger
import os


def load(repo_root, verbose=False):
    """
    Looks for a config file called .pomgenrc in the following locations:
      - <repo_root>/.pomgenrc

    If no config file is found, uses default values.

    Returns a Config instance.
    """
    parser = configparser.RawConfigParser()

    def gen(option, dflt, valid_values=None):
        """Read from [general] section """
        return _get_value_from_config(parser, "general", option, dflt, valid_values)

    def crawl(option, dflt, valid_values=None):
        """Read from [crawler] section """
        return _get_value_from_config(parser, "crawler", option, dflt, valid_values)

    def artifact(option, dflt, valid_values=None):
        """Read from [artifact] section """
        return _get_value_from_config(parser, "artifact", option, dflt, valid_values)

    cfg_path = os.path.join(repo_root, ".pomgenrc")
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            parser.readfp(f)

    pom_template_p = gen("pom_template_path", ["config/pom_template.xml"])

    cfg = Config(
        pom_template_path_and_content=_read_files(repo_root, pom_template_p)[0],
        maven_install_paths=gen("maven_install_paths", ("maven_install.json",)),
        excluded_dependency_paths=crawl("excluded_dependency_paths", ()),
        excluded_src_relpaths=artifact("excluded_relative_paths", ("src/test",)),
        excluded_src_file_names=artifact("excluded_filenames", (".gitignore",)),
        excluded_src_file_extensions=artifact("excluded_extensions", (".md",)),
        transitives_versioning_mode=artifact("transitives_versioning_mode", "semver", valid_values=("semver", "counter")),
        jar_artifact_classifier=artifact("jar_classifier", None),
    )

    if verbose:
        logger.raw("Running with configuration:\n%s\n" % str(cfg))

    return cfg


def _get_value_from_config(parser, section, option, dflt, valid_values):
    try:
        value = parser.get(section, option)
        if valid_values is not None and value not in valid_values:
            raise Exception("Invalid value for %s.%s [%s] - valid values are: %s" % (section, option, value, valid_values))
        return value
    except configparser.NoOptionError:
        return dflt
    except configparser.NoSectionError:
        return dflt


class Config:

    def __init__(self, 
                 pom_template_path_and_content=("",""),
                 maven_install_paths=(),
                 excluded_dependency_paths=(),
                 excluded_src_relpaths=(),
                 excluded_src_file_names=(),
                 excluded_src_file_extensions=(),
                 transitives_versioning_mode="semver",
                 jar_artifact_classifier=None):

        # general
        self.pom_template_path_and_content=pom_template_path_and_content
        self.maven_install_paths = _to_tuple(maven_install_paths)

        # crawler
        self.excluded_dependency_paths = _add_pathsep(_to_tuple(excluded_dependency_paths))

        # artifact
        self.excluded_src_relpaths = _add_pathsep(_to_tuple(excluded_src_relpaths))
        self.excluded_src_file_names = _to_tuple(excluded_src_file_names)
        self.excluded_src_file_extensions = _to_tuple(excluded_src_file_extensions)
        self.transitives_versioning_mode = transitives_versioning_mode
        self._jar_artifact_classifier = jar_artifact_classifier

    @property
    def pom_template(self):
        return self.pom_template_path_and_content[1]

    @property
    def jar_artifact_classifier(self):
        env_var_name = "POMGEN_JAR_CLASSIFIER"
        classifier = os.getenv(env_var_name)
        if classifier is None:
            classifier = self._jar_artifact_classifier
        return classifier

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
maven_install_paths=%s

[crawler]
excluded_dependency_paths=%s

[artifact]
excluded_relative_paths=%s
excluded_filenames=%s
excluded_extensions=%s
transitives_versioning_mode=%s
jar_artifact_classifier=%s
""" % (self.pom_template_path_and_content[0],
       self.maven_install_paths,
       self.excluded_dependency_paths,
       self.excluded_src_relpaths,
       self.excluded_src_file_names,
       self.excluded_src_file_extensions,
       self.transitives_versioning_mode,
       self.jar_artifact_classifier)


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

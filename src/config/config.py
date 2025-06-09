"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Responsible for loading a config file. For the config file format, see /README.md#configuration.
"""


from common import logger
from config import exclusions
import configparser
import os


def load(repo_root, verbose=False):
    """
    Looks for a config file called .pomgenrc in the following locations:
      - <repo_root>/tools/etc/.pomgenrc
      - <repo_root>/tools/.pomgenrc
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

    search_locations = ("tools/etc", "tools", ".")
    for loc in search_locations:
        cfg_path = os.path.join(repo_root, loc, ".pomgenrc")
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f:
                parser.read_file(f)
            if verbose:
                logger.info("Loading configuration at [%s]" % cfg_path)
            break

    pom_template_p = gen("pom_template_path", ["src/config/pom_template.xml"])

    cfg = Config(
        pom_template_path_and_content=_read_files(repo_root, pom_template_p)[0],
        maven_install_paths=gen("maven_install_paths", ("maven_install.json",)),
        locked_requirements_paths=gen("locked_requirements_paths", ()),
        override_file_paths=gen("override_file_paths", ()),
        pom_base_filename=gen("pom_base_filename", "pom"),
        pyproject_base_filename=gen("pyproject_base_filename", "pyproject"),
        excluded_dependency_paths=crawl("excluded_dependency_paths", ()),
        excluded_dependency_labels=crawl("excluded_dependency_labels", ()),
        excluded_src_relpaths=artifact("excluded_relative_paths", ("src/test",)),
        excluded_src_file_names=artifact("excluded_filenames", (".gitignore",)),
        excluded_src_file_extensions=artifact("excluded_extensions", (".md",)),
        transitives_versioning_mode=artifact("transitives_versioning_mode", "semver", valid_values=("semver", "counter")),
        jar_artifact_classifier=artifact("jar_classifier", None),
        change_detection_enabled=artifact("change_detection_enabled", True),
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
        locked_requirements_paths=(),
        override_file_paths=(),
        pom_base_filename="pom",
        pyproject_base_filename="pyproject",
        excluded_dependency_paths=(),
        excluded_dependency_labels=(),
        excluded_src_relpaths=(),
        excluded_src_file_names=(),
        excluded_src_file_extensions=(),
        transitives_versioning_mode="semver",
        jar_artifact_classifier=None,
        change_detection_enabled=True):

        # general
        self.pom_template_path_and_content = pom_template_path_and_content
        self.maven_install_paths = _to_tuple(maven_install_paths)
        self.locked_requirements_paths = _to_tuple(locked_requirements_paths)
        self.override_file_paths = _to_tuple(override_file_paths)
        self.pom_base_filename = pom_base_filename
        self.pyproject_base_filename = pyproject_base_filename

        # crawler
        self.excluded_dependency_paths = _add_pathsep(_to_tuple(excluded_dependency_paths))
        self.excluded_dependency_labels = _to_tuple(excluded_dependency_labels)

        # artifact
        self.excluded_src_relpaths = _add_pathsep(_to_tuple(excluded_src_relpaths))
        self.excluded_src_file_names = _to_tuple(excluded_src_file_names)
        self.excluded_src_file_extensions = _to_tuple(excluded_src_file_extensions)
        self.transitives_versioning_mode = transitives_versioning_mode
        self._jar_artifact_classifier = jar_artifact_classifier
        self._change_detection_enabled = _to_bool(change_detection_enabled)

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
    def change_detection_enabled(self):
        return self._change_detection_enabled

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
override_file_paths=%s
pom_base_filename=%s

[crawler]
excluded_dependency_paths=%s
excluded_dependency_labels=%s

[artifact]
excluded_relative_paths=%s
excluded_filenames=%s
excluded_extensions=%s
transitives_versioning_mode=%s
jar_artifact_classifier=%s
change_detection_enabled=%s
""" % (self.pom_template_path_and_content[0],
       self.maven_install_paths,
       self.override_file_paths,
       self.pom_base_filename,
       self.excluded_dependency_paths,
       self.excluded_dependency_labels,
       self.excluded_src_relpaths,
       self.excluded_src_file_names,
       self.excluded_src_file_extensions,
       self.transitives_versioning_mode,
       self.jar_artifact_classifier,
       self.change_detection_enabled)


def _to_tuple(thing):
    if isinstance(thing, tuple):
        return thing
    elif isinstance(thing, list):
        return tuple(thing)
    elif isinstance(thing, str):
        tokens = thing.split(",")
        filtered_tokens = [t.strip() for t in tokens if len(t.strip()) > 0]
        return tuple(filtered_tokens)
    raise Exception("Cannot convert to tuple [%s] % thing")


def _to_bool(thing):
    if isinstance(thing, bool):
        return thing
    if isinstance(thing, int):
        return False if thing == 0 else True
    if isinstance(thing, str):
        return True if thing.lower() in ("true", "on", "1") else False
    raise Exception("Cannot convert to bool [%s]" % thing)


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

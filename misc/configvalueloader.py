"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Loads pomgen configuration values. Uses the syntax:
<section>.<config-key-name>
"""

import argparse
import sys
from common import common
from config import config as configm


def _parse_arguments(args):
    parser = argparse.ArgumentParser(description="Configuration Value Loader")
    parser.add_argument("--key", type=str, action='append', required=True,
        help="The config key for which to load the value, must be prefixed with the config section name. Can be specified multiple times.")
    parser.add_argument("--separator", type=str, default="|",
        help="The separator to use between values in output (default: |)")
    parser.add_argument("--repo_root", type=str, required=False,
        help="The root of the repository")
    parser.add_argument("--verbose", required=False, action="store_true",
        help="Verbose output")
    return parser.parse_args(args)


def _get_value_from_config(cfg, key):
    """Gets a value from the config object for the given key.

    Args:
        cfg: The config object
        key: The config key (e.g. "artifact.jar_classifier")

    Returns:
        The configuration value from the config object

    Raises:
        ValueError: If the key is unknown
    """
    # this isn't implemented for all config values yet ...
    if key == "artifact.jar_classifier":
        return cfg.jar_artifact_classifier
    elif key == "general.pom_base_filename":
        return cfg.pom_base_filename
    else:
        raise ValueError("Unknown config key [%s], fix me if needed!" % key)


def load_config_values(keys, repo_root, verbose=False):
    """Loads configuration values for multiple keys.

    Args:
        keys: List of config keys (e.g. ["artifact.jar_classifier", "general.pom_base_filename"])
        repo_root: The root of the repository
        verbose: Enable verbose output

    Returns:
        Dictionary mapping keys to their values (None if not configured)

    Raises:
        ValueError: If any key is unknown
    """
    cfg = configm.load(repo_root, verbose)
    result = {}
    for key in keys:
        result[key] = _get_value_from_config(cfg, key)
    return result


def format_output(keys, values, separator):
    """Formats config values as tuple-style output for bash parsing.

    Args:
        keys: List of config keys in the order they were requested
        values: Dictionary mapping keys to their values
        separator: The separator to use between values

    Returns:
        String with values separated by separator (e.g. "value1|value2")
    """
    output_values = []
    for key in keys:
        value = values[key]
        output_values.append(value if value is not None else "None")
    return separator.join(output_values)


if __name__ == "__main__":
    args = _parse_arguments(sys.argv[1:])
    repo_root = common.get_repo_root(args.repo_root)
    try:
        values = load_config_values(args.key, repo_root, args.verbose)
        output = format_output(args.key, values, args.separator)
        print(output)
    except ValueError as e:
        sys.exit(str(e))

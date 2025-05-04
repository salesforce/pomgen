"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Poor man's logger.
Logs to stderr so stdout is 'clean' and only has relevant program output.
"""

import sys

def info(msg):
    _log(msg, "INFO")

def debug(msg):
    _log(msg, "DEBUG")

def error(msg):
    _log(msg, "ERROR")

def warning(msg):
    _log(msg, "WARNING")

def raw(msg):
    sys.stderr.write(msg)

def _log(msg, level):
    sys.stderr.write("[%s] " % level)
    sys.stderr.write(msg)
    sys.stderr.write("\n")


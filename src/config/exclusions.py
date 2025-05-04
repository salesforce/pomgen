"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from collections import namedtuple

SourceExclusions = namedtuple("SourceExclusions", "relative_paths file_names file_extensions")

def src_exclusions(relative_paths=(), file_names=(), file_extensions=()):
    return SourceExclusions(relative_paths, file_names, file_extensions)

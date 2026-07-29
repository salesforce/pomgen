"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module has methods related to calculating and verifying checksums.
"""


import hashlib


def compute_for_external_dependencies(dependencies):
    assert isinstance(dependencies, (list, set, tuple))
    deps = [dep.native_repr for dep in dependencies if not dep.label.is_source_ref]
    deps.sort()
    return hashlib.sha1(str(deps).encode()).hexdigest()

"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module has methods related to calculating and verifying checksums.
"""


import hashlib


def for_dependencies(dependencies):
    assert isinstance(dependencies, (list, set, tuple))
    native_deps = []
    for dep in dependencies:
        native_repr = dep.native_repr
        if dep.label.is_source_ref:
            native_repr = _rm_version(native_repr, dep.version)
        native_deps.append(native_repr)
    native_deps.sort()
    return hashlib.sha1(str(native_deps).encode()).hexdigest()


def _rm_version(native_repr, version):
    version_start_index = native_repr.index(version)
    return native_repr[:version_start_index] + native_repr[version_start_index + len(version):]

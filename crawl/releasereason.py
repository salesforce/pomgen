"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

class ReleaseReason(object):
    FIRST = "artifact has never been released"
    ARTIFACT = "binary artifact changed"
    TRANSITIVE = "transitive dependency changed"
    POM = "pom changed"
    FORCE = "forced release"


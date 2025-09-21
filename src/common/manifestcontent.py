"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


class ManifestContent:
    """
    A container for static manifest content that is passed through to the
    manifest generators.

    IMPORTANT: none of this content can contribute to a manifest difference when
    comparing the current manifest against the previously released manifest.
    See how description is removed in pomparser.format_for_comparison
    
    # TODO lets remove this class

    """
    def __init__(self):
        self._description = None

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        if description is not None:
            description = description.strip()
            if len(description) != 0:
                self._description = description

    def __str__(self):
        return "<description>%s</description>" % self.description


# only the pomgen invocation needs a real instance because this content
# cannot affect manifest diffing
NOOP = ManifestContent()

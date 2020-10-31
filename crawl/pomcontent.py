"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


class PomContent:
    """
    A container for static pom content that is passed through to the pom
    generators.

    IMPORTANT: none of this content can contribute to a pom difference when
    comparing the current pom against the previously released pom.
    See how description is removed in pomparser.format_for_comparison
    """
    def __init__(self):
        # content for the pom <description> element.
        self.description = None


# only the pomgen invocation needs a real instance because this content
# cannot affect pom diffing
NOOP = PomContent()

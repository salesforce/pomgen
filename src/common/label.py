"""
Copyright (c) 2025, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module has abstractions for Bazel labels.
"""

import os


class Label(object):
    """
    Represents a bazel Label.
    """

    def __init__(self, name):
        """
        Initializes a Label with the given string label representation.
        """
        assert name is not None
        name = name.strip()
        if name.endswith("/"):
            name = name[:-1]
        self._name = name

    @property
    def package_path(self):
        """
        Returns the package of this label as a relative path.
        """
        start_index = self._name.find("//")
        if start_index == -1:
            start_index = 0
        else:
            start_index += 2
        target_index = self._name.rfind(":")
        if target_index == -1:
            target_index = len(self._name)
        path = self._name[start_index:target_index]
        if path.endswith("..."):
            path = path[:-3]
        if path.endswith("/"):
            path = path[:-1]
        return path

    @property
    def target(self):
        """
        The bazel target of this label.
        For example, for "//a/b/c:foo", returns "foo".
        """
        i = self._name.rfind(":")
        if i == -1:
            return os.path.basename(self._name)
        return self._name[i+1:]

    @property
    def is_default_target(self):
        """
        Returns True if this label refers to the default target in the package,
        ie the target that has the same name as the directory the BUILD file
        lives in.
        """
        return os.path.basename(self.package_path) == self.target

    @property
    def is_root_target(self):
        """
        Returns True if this label's target is defined in the root BUILD
        file, ie if the label has this pattern "//:"
        """
        return "//:" in self._name

    @property
    def has_repository_prefix(self):
        """
        Whether this label name has a remote repository prefix.
        """
        return self.repository_prefix != ""

    @property
    def repository_prefix(self):
        """
        The repository prefix, or workspace name of this label; empty string if
        this label name doesn't have one.

        For example, for a label like "@pomgen//maven", this method returns
        "@pomgen", for "//foo/path" it returns "".
        """
        if self._name.startswith("@"):
           i = self._name.find("//")
           if i != -1:
               return self._name[0:i]
        return ""
    
    @property
    def is_source_ref(self):
        """
        True if this name is a reference to source in the same repository.
        """
        return self._name.startswith("//")

    @property
    def canonical_form(self):
        """
        Returns the label as a string in its canonical form:

        [@repository]//<package-path>:<target>.

        References to the default target are omitted.
        """
        target = "" if self.is_default_target else ":%s" % self.target
        return "%s//%s%s" % (self.repository_prefix, self.package_path, target)

    def with_target(self, new_target_name):
        """
        Returns a new Label instance with the specified new target name.
        """
        if self.is_default_target:
            label = self.canonical_form
        else:
            label = self.canonical_form[:-(len(self.target)+1)]
        return Label("%s:%s" % (label, new_target_name))

    def __hash__(self):
        return hash((self.repository_prefix, self.package_path, self.target))

    def __eq__(self, other):
        if other is None:
            return False
        return (self.repository_prefix == other.repository_prefix and
                self.package_path == other.package_path and
                self.target == other.target)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return self.canonical_form

    __str__ = __repr__

"""
Copyright (c) 2025, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

This module has abstractions for Bazel labels.
"""


import os


_BUILD_FILE_NAMES = ("BUILD", "BUILD.bazel")


def for_package(root_dir, package_path):
    """
    Returns a label instance for the Bazel package at the given relative path,
    rooted at the given root_dir. Returns None if no build file exists at that
    location.
    """
    for fname in _BUILD_FILE_NAMES:
        rel_path = os.path.join(package_path, fname)
        abs_path = os.path.join(root_dir, rel_path)
        if os.path.isfile(abs_path):
            return Label(rel_path)
    return None


def find_packages(root_dir, package_path=""):
    """
    Walks the directory tree, starting at root dir, and returns a list of
    Label instances for all Bazel packages that exist under the given root_dir.

    If package_path is specified, the search starts at that location.
    """
    labels = []
    for path, dirs, files in os.walk(os.path.join(root_dir, package_path)):
        for fname in files:
            if fname in _BUILD_FILE_NAMES:
                rel_path = os.path.join(os.path.relpath(path, root_dir), fname)
                if rel_path.startswith("./"):
                    # build file at root dir, remove "./" so that the package
                    # of the Label is empty
                    rel_path = rel_path[2:]
                labels.append(Label(rel_path))
    return labels


class Label(object):
    """
    Represents a Bazel Label.
    """

    def __init__(self, name):
        """
        Initializes a Label with the given name, a string. name represents
        a path-like structure with an optional target [path:target].

        If the last path segment is a build file (/BUILD or /BUILD.bazel),
        it is removed from the path.
        
        """
        assert name is not None
        name = name.strip()
        if name.endswith("/"):
            name = name[:-1]
        fname = os.path.basename(name)
        if fname in ("BUILD", "BUILD.bazel"):
            name = os.path.dirname(name)
            self._build_file_name = fname
        else:
            self._build_file_name = None
        self._name = name

    @property
    def name(self):
        """
        The name this instance was initialized with.
        """
        return self._name

    @property
    def package(self):
        """
        The Bazel Package of this label.
        For example, for "//a/b/c:foo", return "//a/b/c"
        """
        i = self._name.find(":")
        if i == -1:
            if self._name.endswith("..."):
                return self._name[:-3]
            return self._name
        return self._name[0:i]

    @property
    def package_path(self):
        """
        Returns the Package of this label as a valid relative path.
        """
        p = self.package
        if p.startswith("//"):
            p = p[2:]
        if p.endswith("/"):
            p = p[:-1]
        return p

    @property
    def target(self):
        """
        The Bazel Target of this label.
        For example, for "//a/b/c:foo", return "foo"
        """
        i = self._name.find(":")
        if i == -1:
            return os.path.basename(self._name)
        return self._name[i+1:]

    @property
    def target_name(self):
        """
        An alias for the "target" property.
        """
        return self.target

    @property
    def is_default_target(self):
        """
        Returns True if this label refers to the default target in the package,
        ie the target that has the same name as the directory the BUILD file
        lives in.
        """
        package = self.package
        target = self.target
        if package is None:
            return False
        if target is None:
            return True
        return os.path.basename(package) == target

    @property
    def is_root_target(self):
        """
        Returns True if this label's target is defined in the root BUILD
        file, ie if the label has this pattern "//:"
        """
        return "//:" in self._name

    @property
    def fqname(self):
        """
        The name of this label with a default repo prefix, iff the 
        initial name did not specify such a prefix and this is not a src ref.
        """
        if self.is_source_ref:
            return self._name
        if self.has_repo_prefix:
            return self._name
        else:
            # the default prefix we use for names without repo prefix:
            # if name is foo, fqname will be @maven//:foo
            # "maven" doesn't really make sense to use anymore, but it isn't
            # clear what to use instead - probably defaulting the repo doesn't
            # make sense
            default_repo = "maven"
            return self.prefix_with(default_repo).name

    @property
    def simple_name(self):
        """
        The name of this label without the remote repo prefix.
        If this label does not have a remote repo prefix, returns just
        its name.
        """
        if self.is_source_ref:
            return self._name
        if self.has_repo_prefix:
            prefix = self.repo_prefix
            return self._name[len(prefix)+4:] # 4 = additional chars @//:
        else:
            return self._name

    @property
    def is_private(self):
        """
        Returns True if this label refers to a private target (starts with ":")
        """
        return self._name.startswith(":")

    @property
    def has_repo_prefix(self):
        """
        Whether this label name has a remote repo prefix.
        """
        return self.repo_prefix is not None

    @property
    def repo_prefix(self):
        """
        The remote repo prefix, or workspace name of this label; None if this
        label name doesn't have one.

        For example, for a label like "@pomgen//maven", returns "pomgen".
        """
        if self._name.startswith("@"):
           i = self._name.find("//")
           if i != -1:
               return self._name[1:i]
        return None
    
    @property
    def is_source_ref(self):
        """
        True if this name is a reference to source in the same repository.
        """
        return self._name.startswith("//")

    @property
    def has_file_extension(self):
        ext = os.path.splitext(self._name)[1]
        return ext in (".jar", ".proto", ".h", ".c", ".cc", ".cpp", ".m", ".py", ".pyc", ".java", ".go")

    @property
    def has_extension_suffix(self):
        return self._name.endswith("_extension")

    @property
    def is_sources_artifact(self):
        return "_jar_sources" in self._name

    @property
    def build_file_path(self):
        """
        The path to the build file of this package, if this Label instance was
        created with a path that pointed to a build file.
        None if this Label instance does not know about the build file it was
        created for.
        """
        if self._build_file_name is None:
            return None
        return os.path.join(self.package_path, self._build_file_name)

    def prefix_with(self, repo_prefix):
        """
        Returns a new Label instance that is qualified with the
        specified repo_prefix. This method asserts that this instance is not
        already fully qualified.        
        """
        assert not self.has_repo_prefix, "This label already has a repo prefix: %s" % self._name
        return Label("@%s//:%s" % (repo_prefix, self._name))

    def with_target(self, target):
        """
        Returns a new Label instance that has the specified target.
        """
        return Label("%s:%s" % (self.package, target))

    def as_wildcard_label(self, wildcard):
        if wildcard == "...":
            return Label("%s/%s" % (self.package, wildcard))
        else:
            return Label("%s:%s" % (self.package, wildcard))

    def as_alternate_default_target_syntax(self):
        """
        Labels may omit the target if they refer to the default target, or they
        may not omit it. If this Label instance refers to the default target,
        this method returns the other syntax.
        So:
            Given this Label instance is: //a/b/c, returns //a/b/c:c
            Or, given this Label instance is //a/b/c:c, returns //a/b/c
        """
        assert self.is_default_target, "label must refer to the default target"
        if ":" in self.name:
            return Label(self.package)
        else:
            return Label("%s:%s" % (self.package, self.target))

    def __hash__(self):
        return hash((self.package_path, self.target))

    def __eq__(self, other):
        if other is None:
            return False
        return self.package_path == other.package_path and self.target == other.target

    def __ne__(self, other):
        return not self == other

    def __len__(self):
        return len(self._name)

    def __repr__(self):
        return self._name

    __str__ = __repr__

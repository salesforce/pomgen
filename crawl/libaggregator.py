"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl.releasereason import ReleaseReason


def get_libraries_to_release(artifact_nodes):
    """
    Takes an artifact DAG and turns it into a library DAG.
    """
    library_path_to_library_node = {}
    library_nodes = []
    for artifact_node in artifact_nodes:
        add = artifact_node.artifact_def.library_path not in list(library_path_to_library_node.keys())
        n = _walk(artifact_node, library_path_to_library_node)
        if add:
            library_nodes.append(n)

    return library_nodes


class LibraryNode:

    ALL_LIBRARY_NODES = []

    def __init__(self, library_path, requires_release, release_reason, version,
                 released_version, version_increment_strategy_name):
        self.library_path = library_path
        self.requires_release = requires_release
        self.release_reason = release_reason
        self.version = version
        self.released_version = released_version
        self.version_increment_strategy_name = version_increment_strategy_name
        self._library_path_to_child_node = {}
        LibraryNode.ALL_LIBRARY_NODES.append(self)

    def add_child(self, node):
        if node.library_path == self.library_path:
            pass
        elif node.library_path in list(self._library_path_to_child_node.keys()):
            pass
        else:
            self._library_path_to_child_node[node.library_path] = node

    @property
    def children(self):
        return list(self._library_path_to_child_node.values())

    def pretty_print(self):
        """
        Traverses tree and returns "pretty" text representation.
        """
        output_lines = []
        all_release_reasons = set()
        node_path = []
        self._pretty_print(0, output_lines, all_release_reasons, node_path)
        pretty_tree = '\n'.join(output_lines)
        legend = ["%s %s" % (LibraryNode._get_rel_indicator(r).rjust(2),
                             r if r is not None else "no changes to release")
                  for r in all_release_reasons]
        return "%s\n\n%s" % (pretty_tree, '\n'.join(legend))

    def _pretty_print(self, indent, output_lines, all_release_reasons, node_path):
        release_reason = self.release_reason if self.requires_release else None
        all_release_reasons.add(release_reason)
        indicator = LibraryNode._get_rel_indicator(release_reason)
        output_lines.append("%s%s %s %s" % (' '*indent, self.library_path,
                                            indicator, 
                                            self._get_pretty_print_version()))
        if self in node_path:
            # detected circular reference between library nodes, stop recursing
            output_lines.append("%s..." % (' '*indent))
        else:
            for child in self.children:
                child._pretty_print(indent+2, output_lines, all_release_reasons, node_path + [self])

    def _get_pretty_print_version(self):
        # version can be none for libraries that have no artifact producing
        # package
        return "" if self.version is None else self.version

    @classmethod
    def _get_rel_indicator(self, release_reason):
        if release_reason is None:
            return "-" # not released
        elif release_reason == ReleaseReason.TRANSITIVE:
            return "*"
        elif release_reason == ReleaseReason.POM:
            return "#"
        elif release_reason == ReleaseReason.ARTIFACT:
            return "+"
        elif release_reason == ReleaseReason.FIRST:
            return "++"
        elif release_reason == ReleaseReason.ALWAYS:
            return "!"
        elif release_reason == ReleaseReason.UNCOMMITTED_CHANGES:
            return "<>"
        else:
            raise Exception("Unhandled release reason: %s - this is a bug" % self.release_reason)

    def __str__(self):
        return self.library_path

    __rep__ = __str__

    
def _walk(artifact_node, library_path_to_library_node):
    artifact_def = artifact_node.artifact_def
    library_path = artifact_def.library_path
    if library_path in list(library_path_to_library_node.keys()):
        library_node = library_path_to_library_node[library_path]
        # only the release_reason needs to be re-computed here -
        # the LibraryNode's "requires_release" attribute doesn't need to be set
        # because all artifacts belonging to the same library already have their
        # "requires_release" attribute set consistently (either all True or all
        # False) - therefore the LibraryNode's require_release attribute was
        # already set correctly when the LibraryNode was instantiated
        library_node.release_reason = _get_lib_release_reason(library_node.release_reason, artifact_def.release_reason)
    else:
        version = artifact_def.version if artifact_def.requires_release else artifact_def.released_version
        if version is None:
            # make sure that version is None for the expected reason:
            assert not artifact_def.pom_generation_mode.produces_artifact
        library_node = LibraryNode(library_path, artifact_def.requires_release,
                                   artifact_def.release_reason, version,
                                   artifact_def.released_version,
                                   artifact_def.version_increment_strategy_name)
        library_path_to_library_node[library_path] = library_node
        
    for artifact_child_node in artifact_node.children:
        # traverse the artifact children - they may or may not belong to the
        # same library
        library_child_node = _walk(artifact_child_node,library_path_to_library_node)
        library_node.add_child(library_child_node)
    return library_node


def _get_lib_release_reason(current_release_reason, proposed_release_reason):
    """
    Individual artifacts for a single library may have different release 
    reasons.  For example, one may have changed because code was changed,
    another one may be a pom-only change.
    Since we are concerned with libraries here, not artifacts, this method
    defines the precedence for release reasons.
    """
    if current_release_reason == ReleaseReason.ALWAYS:
        pass
    if current_release_reason == ReleaseReason.FIRST:
        if proposed_release_reason in (ReleaseReason.ALWAYS,):
            return proposed_release_reason
    if current_release_reason == ReleaseReason.UNCOMMITTED_CHANGES:
        if proposed_release_reason in (ReleaseReason.FIRST,
                                       ReleaseReason.ALWAYS,):
            return proposed_release_reason
    if current_release_reason == ReleaseReason.ARTIFACT:
        if proposed_release_reason in (ReleaseReason.FIRST,
                                       ReleaseReason.ALWAYS,
                                       ReleaseReason.UNCOMMITTED_CHANGES,):
            return proposed_release_reason
    if current_release_reason == ReleaseReason.POM:
        if proposed_release_reason in (ReleaseReason.FIRST,
                                       ReleaseReason.ALWAYS,
                                       ReleaseReason.ARTIFACT,
                                       ReleaseReason.UNCOMMITTED_CHANGES,):
            return proposed_release_reason
    if current_release_reason == ReleaseReason.TRANSITIVE:
        if proposed_release_reason in (ReleaseReason.FIRST,
                                       ReleaseReason.ALWAYS,
                                       ReleaseReason.ARTIFACT,
                                       ReleaseReason.POM,
                                       ReleaseReason.UNCOMMITTED_CHANGES):
            return proposed_release_reason

    return current_release_reason


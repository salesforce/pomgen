"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

Bazel BUILD file related logic.
"""
import common.bazel as bazel
import common.genmode as genmode
import common.label as labelm
import os


def load_dependencies(repository_root_path, artifact_def, label, verbose=False):
    """
    Loads all dependencies that the specified label, owned by the given
    artifact_def, depends on.

    Returns a list of common.label.Label instances.
    """
    assert artifact_def is not None
    assert label is not None, "label is None for artifact %s" % artifact_def
    labels = ()
    if artifact_def.deps is not None:
        labels = [labelm.Label(lbl) for lbl in artifact_def.deps]
    if artifact_def.generation_mode.query_dependency_attributes:
        labels += bazel.query_dependencies(repository_root_path, artifact_def,
                                           label, verbose)
    return labels


def partition_and_filter_labels(labels, downstream_artifact_def, workspace):
    """
    For the given labels, filters and partitions by source labels.
    Returns a tuple of source labels and dependencies.
    """
    assert downstream_artifact_def is not None
    source_labels = []
    deps = []
    for lbl in labels:
        lbl = _filter_label(lbl, downstream_artifact_def, workspace)
        if lbl is None:
            continue
        add_dependency = True
        artifact_def = None
        if downstream_artifact_def.generation_strategy.is_source_ref(lbl):
            source_labels.append(lbl)
            artifact_def = workspace.parse_maven_artifact_def(lbl.package_path, downstream_artifact_def)
            if artifact_def.generation_mode is genmode.ONEONEONE_CHILD:
                if artifact_def.is_or_has_same_111_parent(downstream_artifact_def):
                    # the referenced package (//label) belongs to the same
                    # 111 module, so we don't add any dep
                    add_dependency = False
                else:
                    # we need to point to the main 111 parent when building
                    # the dep, since it has the full metadata, including
                    # the aggregation target
                    artifact_def = artifact_def.parent_artifact_def
            else:
                if not artifact_def.generation_mode.produces_artifact:
                    add_dependency = False
        if add_dependency:
            dep = downstream_artifact_def.generation_strategy.load_dependency(lbl, artifact_def)
            if dep is not None:
                deps.append(dep)
    return source_labels, deps


def _filter_label(label, downstream_artifact_def, workspace):
    assert label is not None
    assert downstream_artifact_def is not None
    assert workspace is not None
    if label in workspace.excluded_dependency_labels:
        return None
    elif downstream_artifact_def.generation_strategy.is_source_ref(label):
        for excluded_path in workspace.excluded_dependency_paths:
            # globally defined path exclusions are relative to the
            # repository root
            if label.package_path.startswith(excluded_path):
                return None
        for excluded_path in downstream_artifact_def.excluded_dependency_paths:
            # per-artifact exclusions are relative to the artifact package
            excluded_path = os.path.join(downstream_artifact_def.bazel_package, excluded_path)
            if label.package_path.startswith(excluded_path):
                return None
        artifact_def = workspace.parse_maven_artifact_def(label.package_path, downstream_artifact_def)
        if artifact_def is None:
            if bazel.is_never_link_dep(workspace.repo_root_path, label.canonical_form):
                return None
            else:
                raise Exception("cannot process this package because there is no manifest metadata at: [%s]" % label.package_path)
    return label

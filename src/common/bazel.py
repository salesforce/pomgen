"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


This module has functions that return information about the bazel build graph
structure.  Whenever possible, the code here uses bazel query.
"""
import common.label as labelm
import common.logger as logger
import common.os_util as os_util
import os


def query_dependencies(repository_root_path, artifact_def, label, verbose=False):
    """
    Delegates to bazel query to get the value of the specified bazel target's
    "deps" and "runtime_deps" attributes. The bazel target is provided by the
    given artifact_def instance.
    Returns an iterable of common.label.Label instances.
    """
    if not artifact_def.include_deps:
        return ()
    else:
        assert artifact_def.bazel_package is not None
        try:
            labels = _query_java_library_deps_attributes(
                repository_root_path,
                label.canonical_form,
                artifact_def.generation_mode.dependency_attributes,
                verbose)
            labels = [labelm.Label(lbl) for lbl in labels]
            return _remove_package_private_labels(labels, artifact_def)
        except Exception as e:
            raise Exception("Error while querying dependencies of %s. Maybe the label [%s] does not exist?\n%s" % (artifact_def, label.canonical_form, repr(e)))


def _query_java_library_deps_attributes(repository_root_path, target_pattern,
                                        dep_attributes, verbose=False):
    """
    Returns, as a list of strings, the combined values of the dep_attributes
    given, typically 'deps' and 'runtime_deps', of the (java_library) rule
    identified by the specified target_pattern.

    Example return value:

        ["@com_google_guava_guava//jar",
         "@com_github_ben_manes_caffeine_caffeine//jar",
         "//projects/libs/servicelibs/srpc/srpc-api"]

    If the target name is not specified explicitly, it is defaulted based on
    the package name.

    target_pattern examples:
      - //projects/libs/foo:blah
        -> look for a target called "blah" in the "foo" package
      - //projects/libs/foo
        -> look for a target called "foo" in the "foo" package (the target name
           is defaulted based on the package name)
    """
    if target_pattern.endswith("..."):
        raise Exception("target_pattern must be more specific")

    query_parts = ["labels(%s, %s)" % (attr, target_pattern) for attr in dep_attributes]
    query = "bazel query --noimplicit_deps --order_output full '%s'" % " union ".join(query_parts)
    if verbose:
        logger.debug("Running query: %s" % query)
    output = os_util.run_cmd(query, cwd=repository_root_path).splitlines()
    deps = _sanitize_deps(output)
    deps = _ensure_unique_deps(deps)
    return reversed(deps)


def _remove_package_private_labels(labels, owning_artifact_def):
    """
    This method removes labels that point back to the bazel package
    of the current artifact (so private targets in the same build file),
    except when no actual artifact is produced (-> the special "skip"
    generation mode).
     Specifically, this method handles the case where, in the BUILD file,
    a java_library has a dependency on a (private) target defined in the
    same Bazel Package. This configuration is generally not supported.
    """
    updated_labels = []
    for label in labels:
        if label.package_path == owning_artifact_def.bazel_package:
            # this label has the same package as the artifact referencing it
            # is is therefore a private target ref - skip it unless this
            # package does not produce any artifact
            if owning_artifact_def.generation_mode.produces_artifact:
                continue
        updated_labels.append(label)
    return updated_labels


def query_all_libraries(repository_root_path, packages, generation_strategy_factory, verbose=False):
    """
    Given a list of packages (directories), walks the paths up to find the root
    library directories, and returns those (without duplicates).
    """
    lib_roots = set()
    for package in packages:
        while len(package) > 0 and package != '/':
            abs_package_path = os.path.join(repository_root_path, package)
            if verbose:
                logger.debug("Checking path for library [%s]" % abs_package_path)
            if generation_strategy_factory.get_strategy_for_library_package(abs_package_path) is not None:
                if verbose:
                    logger.debug("Found library [%s]" % package)
                lib_roots.add(package)
                break
            else:
                package = os.path.dirname(package)
    return sorted(lib_roots)


def _sanitize_deps(deps):
    updated_deps = []
    for dep in deps:
        sanitized = _sanitize_dep(dep)
        if sanitized is not None:
            updated_deps.append(dep)
    return updated_deps


def _sanitize_dep(dep):
    if dep.startswith('@'):
        if dep.endswith(":jar"):
            return dep[:-4] # remove :jar suffix
        dep_split = dep.split(':')
        if len(dep_split) == 2 and len(dep_split[1]) > 0:
            return dep_split[1]
    elif dep.startswith("//"):
        return dep
    # dep is not something we want, ignore (e.g. log lines from tools/bazel can fall into here)
    return None


def _ensure_unique_deps(deps):
    updated_deps = []
    s = set()
    for dep in deps:
        if dep not in s:
            updated_deps.append(dep)
            s.add(dep)
    return updated_deps


def is_never_link_dep(repository_root_path, package):
    """
    Check if the dependency has neverlink set to 1
    java_library with neverlink set to 1 should not be considered because required only at compilation time
    Bazel ref: https://docs.bazel.build/versions/main/be/java.html#java_library.neverlink:~:text=on%20this%20target.-,neverlink,-Boolean%3B%20optional%3B%20default
    """
    query = "bazel query 'attr('neverlink', 1, %s)'" % package
    stdout = os_util.run_cmd(query, cwd=repository_root_path)
    return package in stdout

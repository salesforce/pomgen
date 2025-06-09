"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Crawls Bazel BUILD file dependencies and builds a DAG.
"""
from collections import defaultdict
from common import label as labelm
from common import logger
from crawl import artifactgenctx
from crawl import bazel
from crawl import buildpom
from crawl import dependency
from crawl import pom
from crawl import pomparser
from crawl.releasereason import ReleaseReason
import difflib
import os


class Node:
    """
    A single node in the DAG, based on references in BUILD files.
    Each Bazel target gets its own Node instance. Typically, there is one 
    target per bazel package.
    """

    def __init__(self, parent, artifact_def, label):
        assert artifact_def is not None, "artifact_def cannot be None"
        assert label is not None, "label cannot be None"

        # the parent Nodes
        self.parents = [] if parent is None else [parent]
        # parsed metadata (BUILD.pom etc) files
        self.artifact_def = artifact_def
        # the dependency pointing to this target
        self.label = label
        # all direct child nodes
        self.children = []

    def pretty_print(self):
        self._pretty_print(self, 0)

    def _pretty_print(self, node, indent):
        print("%s%s:%s" % (' '*indent, node.artifact_def.group_id, node.artifact_def.artifact_id))
        for child in node.children:
            self._pretty_print(child, indent+2)


class CrawlerResult:
    """
    Useful bits and pieces that are the outcome of crawling Bazel BUILD files.
    """
    def __init__(self, genctxs, nodes, crawled_bazel_packages):

        # artifactgenctx.ArtifactGenerationContext instances
        self.artifact_generation_contexts = genctxs

        # list of root nodes
        self.nodes = nodes

        # set of Dependency instances, for all crawled bazel packages
        self.crawled_bazel_packages = crawled_bazel_packages


class Crawler:

    def __init__(self, workspace, verbose=False):
        self.workspace = workspace
        self.verbose = verbose # verbose logging
        self.package_to_artifact = {} # bazel package -> artifact def instance
        self.library_to_artifact = defaultdict(list) # library root path -> list of its artifact def instances
        self.library_to_nodes = defaultdict(list) # library root path -> list of its DAG Node instances
        self.target_to_node = {} # label.Label -> Node for that target
        self.target_to_dependencies = {} # label.Label -> target's deps

        self.genctxs = [] # ArtifactGenerationContext instances
        self.leafnodes = [] # all leafnodes discovered while crawling

    def crawl(self, packages, follow_references=True, force_release=False):
        """
        Crawls Bazel BUILD file dependencies, starting at the specified
        Bazel packages.

        Builds up a DAG of Node instances based on the references in BUILD
        files.
        
        Arguments:

        follow_references: 
            If False, this crawler will not crawl BUILD file references, 
            only processing the packages passed into this method

            This is typically only used for debugging.

        force_release:
            Mark all artifacts as requiring to be released

        Returns a CrawlerResult instance.
        """


        # first we build the initial DAG, by starting with one or more packages
        # and traversing references expressed in BUILD files, specifically
        # deps and runtime deps of single java_library target.
        # there must be only one java_library target defined in each processed
        # bazel package/BUILD file
        nodes = self._crawl_packages(packages, follow_references)
        if self.verbose:
            self._print_debug_output(nodes, "After initial crawl")


        # a library (LIBRARY.root) may have more than one artifact (Bazel
        # package with a BUILD.pom file). since we always release all artifacts
        # belonging to a library together, we need to make sure to gather all
        # artifacts for all libraries referenced. gathering artifacts may drag
        # in more artifacts in different libraries, so we continue until there
        # are no artifacts left to process
        if follow_references:
            missing_packages = self._get_unprocessed_packages()
            if len(missing_packages) > 0:
                while len(missing_packages) > 0:
                    if self.verbose:
                        logger.debug("Discovered additional packages %s" % missing_packages)
                    nodes += self._crawl_packages(missing_packages, follow_references)
                    missing_packages = self._get_unprocessed_packages()

                if self.verbose:
                    self._print_debug_output(nodes, "After adding missing packages")
            else:
                if self.verbose:
                    self._print_debug_banner("No missing packages found")


        # crawling is complete at this point, now process the nodes
        
        # for bazel targets that do not generate a pom 
        # (pom_generation_mode=skip), we still need to handle dependencies;
        # this is the "import bundle" use case.
        # push the dependencies up to the closest parent node that does
        # generate a pom
        self._push_transitives_to_parent()


        # computing the set of dependencies for each Node is done

        # now compute the transitive closure of deps for each node
        target_to_transitive_closure_deps = self._compute_transitive_closures_of_deps()


        # add discovered deps to artifact generation contexts
        self._register_dependencies(target_to_transitive_closure_deps)


        # for each artifact, if its manifest (for ex pom.xml) has changed since
        # the last release (tracked by pom.xml.released), mark the artifact as
        # requiring to be released
        self._check_for_artifact_manifest_changes()


        # figure out whether artifacts need to be released because a transitive
        # dependency needs to be released
        self._calculate_artifact_release_flag(force_release)


        # include only contexts for artifacts that need to be released
        # included in the result
        ctxs = [ctx for ctx in self.genctxs if ctx.artifact_def.requires_release]

        crawled_bazel_packages = self._get_crawled_packages_as_deps()

        return CrawlerResult(ctxs, nodes, crawled_bazel_packages)

    def _register_dependencies(self, target_to_transitive_closure_deps):
        """
        This method sets dependency lists on generation contexts:

        - the direct dependencies of the artifact
        - the transitive closure of the direct dependenices
        - the transitive closure of the library's dependencies
        """
        for ctx in self.genctxs:
            directs = self.target_to_dependencies[ctx.label]
            ctx.register_artifact_directs(directs)
            transitive_closure = target_to_transitive_closure_deps[ctx.label]
            ctx.register_artifact_transitive_closure(transitive_closure)
            lib_transitive_closure = self\
                ._get_deps_transitive_closure_for_library(
                    ctx.artifact_def.library_path,
                    target_to_transitive_closure_deps)
            ctx.register_library_transitive_closure(lib_transitive_closure)

    def _get_deps_transitive_closure_for_library(
            self, library_path, target_to_transitive_closure_deps):
        all_deps = set()

        nodes = self.library_to_nodes[library_path]
        for n in nodes:
            all_deps.update(target_to_transitive_closure_deps[n.label])

        # also include every artifact that is part of this library
        # (we have already collected them above if they all reference each
        # other, but these references are not guaranteed)
        artifacts = self.library_to_artifact[library_path]
        for art_def in artifacts:
            all_deps.add(dependency.new_dep_from_maven_artifact_def(art_def))
        return all_deps

    def _get_crawled_packages_as_deps(self):
        deps = [dependency.new_dep_from_maven_artifact_def(art_def) for art_def in self.package_to_artifact.values()]
        deps = set(self._filter_non_artifact_referencing_deps(deps))
        return deps

    def _get_unprocessed_packages(self):
        """
        For each crawled library, ensure we have included all its packages 
        (each package with a BUILD.pom file is a single maven artifact)
        
        Returns a list of strings, the paths to the packages that need to be
        handled.
        """
        all_packages_already_processed = set(self.package_to_artifact.keys())
        processed_libraries = set()
        all_artifacts = list(self.package_to_artifact.values())
        missing_packages = []
        for artifact_def in all_artifacts:
            library_path = artifact_def.library_path
            if library_path not in processed_libraries:
                processed_libraries.add(library_path)
                all_library_packages = set(
                    self._query_all_artifact_sub_packages(
                        library_path, artifact_def.generation_strategy))
                missing_packages += all_library_packages.difference(all_packages_already_processed)
        return missing_packages

    def _query_all_artifact_sub_packages(self, library_path, generation_strategy):
        maven_artifact_packages = []
        path = os.path.join(self.workspace.repo_root_path, library_path)
        for rootdir, dirs, files in os.walk(path):
            md_file_path = os.path.join(rootdir, generation_strategy.metadata_path)
            if os.path.exists(md_file_path):
                relpath = os.path.relpath(rootdir, self.workspace.repo_root_path)
                maven_artifact_packages.append(relpath)
        return maven_artifact_packages

    def _check_for_artifact_manifest_changes(self):
        """
        For each artifact def not flagged as needing to be released, check 
        whether its current manifest (for ex pom.xml) is different the
        previously released manifest. If it has changed, mark the artifact def
        as needing to be released.
        """
        for ctx in self.genctxs:
            art_def = ctx.artifact_def
            if not art_def.requires_release and art_def.released_pom_content is not None:
                generator = art_def.generation_strategy.new_generator(ctx)
                goldfile_manifest = generator.gen(pom.PomContentType.GOLDFILE)
                current_manifest = pomparser.format_for_comparison(goldfile_manifest)
                previous_manifest = pomparser.format_for_comparison(art_def.released_pom_content)
                manifest_changed = current_manifest != previous_manifest
                if manifest_changed:
                    art_def.requires_release = True
                    # TODO release reason
                    art_def.release_reason = ReleaseReason.POM

                    if self.verbose:
                        logger.debug("pom diff %s %s" % (art_def, art_def.bazel_package))
                        diff = difflib.unified_diff(previous_manifest.splitlines(True), current_manifest.splitlines(True))
                        logger.raw(''.join(diff))
                        logger.debug("%s computed manifest:" % art_def)
                        logger.raw(current_manifest)
                        logger.debug("%s released manifest:" % art_def)
                        logger.raw(previous_manifest)


    def _compute_transitive_closures_of_deps(self):
        """
        For every target, compute its full transitive closure of deps.
        
        Returns a dictionary: target -> iterable of deps (transitive closure)

        For example, with targets:
        A->B->C, each target referencing also some other (3rd party) 
        dependencies, the deps returns for A include the deps of B and C.

        Algorithm: we just walk up from the leafnodes to parents, accumulating
        deps along the way.

        Note that this method requires the target_to_dependencies dictionary
        to be up-to-date.
        """
        target_to_all_dependencies = {}
        for node in self.leafnodes:
            accumulated_deps = []
            self._accumulate_deps_and_walk(node, accumulated_deps,
                                           target_to_all_dependencies)
        return target_to_all_dependencies

    def _accumulate_deps_and_walk(self, node, accumulated_deps,
                                  target_to_all_dependencies):
        """
        node: the current node to process
        accumulated_deps: a list of deps, each node's deps are added to to it
        target_to_all_dependencies: the result dictionary being built
        """
        this_node_deps = self.target_to_dependencies[node.label]

        processed_deps = set() # to remove duplicate deps

        this_node_all_deps = [] # the list we are building in this method

        processed_deps.update(this_node_deps)

        for dep in this_node_deps:
            # add each dep that is explicitly listed in the BUILD file
            this_node_all_deps.append(dep)
            # for each explicitly listed dep, we add the transitive closure of
            # Maven deps
            # this is an extra lookup because these may not be listed in the
            # BUILD file
            transitives = node.artifact_def.generation_strategy.load_transitive_closure(dep)
            for transitive in transitives:
                if transitive not in processed_deps:
                    # only add the transitive if it isn't explicitly listed
                    # in the BUILD file and if it wasn't already a handled
                    # transitive from a previous dep
                    this_node_all_deps.append(transitive)
                    processed_deps.add(transitive)


        # when encountering a duplicate dep, we keep this order:
        # 1) current deps from target
        # 2) previous transitive closure computation
        # 3) accumulated deps from child

        this_node_current_transitives = target_to_all_dependencies.get(node.label, ())
        this_node_all_deps += [d for d in this_node_current_transitives if d not in processed_deps]
        processed_deps.update(this_node_all_deps)

        this_node_all_deps += [d for d in accumulated_deps if d not in processed_deps]
        processed_deps.update(this_node_all_deps)

        target_to_all_dependencies[node.label] = this_node_all_deps

        for parent in node.parents:
            accumulated_deps = this_node_all_deps + [d for d in accumulated_deps if d not in processed_deps]
            self._accumulate_deps_and_walk(parent, accumulated_deps,
                                           target_to_all_dependencies)

    def _push_transitives_to_parent(self):
        """
        For special pom generation modes that do not actually produce
        maven artifacts (pom_generation_mode="skip"):
        Given artifacts A->B->C->D, if B and C have "skip" generation mode,
        their deps need to be pushed up to A, so that they are included in
        A's pom.xml. So the final poms generated will be: A->D
        """
        for node in self.leafnodes:
            processed_nodes = set() # Node instances that were already handled
            collected_dep_lists = [] # list of list of deps
            self._push_transitives_and_walk(node, collected_dep_lists, 
                                            processed_nodes)

    def _push_transitives_and_walk(self, node, collected_dep_lists, 
                                   processed_nodes):
        deps = self.target_to_dependencies[node.label]
        if node.artifact_def.pom_generation_mode.produces_artifact:
            if len(collected_dep_lists) > 0:
                deps = self.target_to_dependencies[node.label]
                collected_dep_lists.append(deps)
                deps = self._process_collected_dep_lists(collected_dep_lists)
                self.target_to_dependencies[node.label] = deps
                collected_dep_lists = []
        else:
            if node not in processed_nodes:
                processed_nodes.add(node)
                collected_dep_lists.append(deps)
        for parent in node.parents:
            # important: for each recursive call, we create a copy of
            # collected_dep_lists, because otherwise updates to this list
            # from recursive calls are visible here
            self._push_transitives_and_walk(parent, list(collected_dep_lists),
                                            processed_nodes)

    def _process_collected_dep_lists(self, collected_dep_lists):
        deps = reversed(collected_dep_lists)
        deps = self._flatten_and_dedupe(deps)
        deps = self._filter_non_artifact_referencing_deps(deps)
        return deps

    def _flatten_and_dedupe(self, list_of_lists):
        flattened = []
        processed = set()
        for li in list_of_lists:
            for item in li:
                if item not in processed:
                    flattened.append(item)
                    processed.add(item)
        return flattened

    def _filter_non_artifact_referencing_deps(self, deps):
        return [d for d in deps if d.references_artifact]

    def _calculate_artifact_release_flag(self, force_release):
        """
        Given libraries A->B->C->D, if only C changed, we need to also mark
        the reverse transitive deps as having changed, so that we end up
        releasing A, B and C.

        If force_release is set, all artifacts are marked as requiring 
        releasing.
        """
        # we start with a leafnode, and walk up (the leaf nodes represent
        # packages/maven artifacts, not libraries)
        for node in self.leafnodes:
            if self.verbose:
                print("Propagating release state, starting at leaf node", node.artifact_def.bazel_package)
            processed_nodes = set()
            self._propagate_req_rel(node,
                                    transitive_dep_requires_release=False,
                                    force_release=force_release,
                                    processed_nodes=processed_nodes)

    def _propagate_req_rel(self, node, transitive_dep_requires_release, force_release, processed_nodes):
        if node in processed_nodes:
            return
        processed_nodes.add(node)
        art_def = node.artifact_def
        library_path = art_def.library_path
        all_artifact_defs = self.library_to_artifact[library_path]
        assert len(all_artifact_defs) > 0, "expected some artifact defs"
        sibling_artifact_requires_release, sibling_release_reason = self._any_artifact_requires_releasing(all_artifact_defs)
        if (force_release or
            sibling_artifact_requires_release or
            transitive_dep_requires_release):
            if self.verbose:
                if force_release:
                    print("Library", library_path, "requires release because force is enabled")
                elif sibling_artifact_requires_release:
                    print("Library", library_path, "requires release because", sibling_release_reason, "propagating to parent lib(s)")
                elif transitive_dep_requires_release:
                    print("Library", library_path, "requires release because a child lib requires to be released")
                else:
                    assert False, "bug"
            # update all artifacts belonging to the library at once
            updated_artifact_defs = []
            for artifact_def in all_artifact_defs:
                if force_release or not artifact_def.requires_release:
                    artifact_def.requires_release = True
                    updated_artifact_defs.append(artifact_def)
                    if force_release:
                        artifact_def.release_reason = ReleaseReason.ALWAYS
                    else:
                        if sibling_artifact_requires_release:
                            artifact_def.release_reason = sibling_release_reason
                        elif transitive_dep_requires_release:
                            artifact_def.release_reason = ReleaseReason.TRANSITIVE
                        else:
                            raise Exception("release_reason not set on artifact - this is a bug")
        else: # release not required
            if self.verbose:
                print("Library", library_path, "does not required to be released")
        # process all artifact nodes belonging to the current library, 
        # otherwise we may miss some references to other libraries
        all_artifact_nodes = self.library_to_nodes[library_path]
        for n in all_artifact_nodes:
            for parent in n.parents:
                if parent.artifact_def.library_path == n.artifact_def.library_path:
                    # no need to crawl within the same library
                    continue
                if n.artifact_def.requires_release and not force_release:
                    transitive_dep_requires_release = True
                self._propagate_req_rel(parent,
                                        transitive_dep_requires_release,
                                        force_release,
                                        processed_nodes)

    def _crawl_packages(self, packages, follow_references):
        """
        Returns a list of Node instances, one for each of the specified Bazel
        packages (directories). Each package must have a BUILD.pom file,
        as well as a LIBRARY.root file, either in the same directory as the 
        BUILD.pom file or in a parent directory (for libraries with more than
        one artifact).
        
        follow_references: 
            If False, this method doesn't follow BUILD file references.
        """
        nodes = []
        for package in packages:
            parent_node = None
            label = labelm.Label(package)
            node = self._crawl(label, parent_node, follow_references)
            nodes.append(node)
        return nodes

    def _crawl(self, label, parent_node, follow_references):
        """
        Loads and processes the dependencies of the given label. For each source
        reference, calls this method recursively, unless follow_references is
        False.

        Args:
            label:
                label.Label instance
            parent_node:
                The downstream that references this package, crawler.Node
            follow_references:
                Bool

        Returns a Node instance for the crawled package.
        """
        assert isinstance(label, labelm.Label)
        artifact_def = self.workspace.parse_maven_artifact_def(label.package_path)
        if artifact_def is None:
            raise Exception("No artifact defined at package %s" % label)
        label = Crawler._merge(label, artifact_def)
        if label in self.target_to_node:
            # if we have already processed this target, we can re-use the
            # children we discovered previously
            # for example: A -> B -> C is how we found B, and now we got here
            # through another path: A -> Z -> B -> C
            # the parent is different, but the children have to be the same
            cached_node = self.target_to_node[label]
            if self.verbose:
                logger.debug("Skipping re-crawling of artifact [%s] with target key [%s]" % (cached_node.artifact_def, label))
            # also add the new parent to the cached_node - this is important
            # because we have logic that traverses the nodes from children to
            # parent nodes
            if parent_node is not None:
                assert parent_node not in cached_node.parents
                cached_node.parents.append(parent_node)
                if self.verbose:
                    logger.debug("Adding new parent [%s] to cached node [%s]" % (parent_node.artifact_def.bazel_package, cached_node.artifact_def.bazel_package))
            return cached_node
        else:
            if self.verbose:
                logger.info("Processing [%s]" % label)
            
            self.package_to_artifact[label.package_path] = artifact_def
            self.library_to_artifact[artifact_def.library_path].append(artifact_def)

            artifactctx = artifactgenctx.ArtifactGenerationContext(
                self.workspace, artifact_def, label)
            self.genctxs.append(artifactctx)
            labels = self._discover_dependencies(artifact_def, label)
            source_labels, deps = self._partition_and_filter_labels(
                labels, artifact_def.generation_strategy)
            if self.verbose:
                logger.debug("Determined labels for artifact: [%s] with target key [%s]" % (artifact_def, label))
                logger.debug("Labels: %s" % "\n".join([lbl.canonical_form for lbl in labels]))
                logger.debug("Dependencies: %s" % "\n".join([str(d) for d in deps]))
            self.target_to_dependencies[label] = deps
            node = Node(parent_node, artifact_def, label)
            if follow_references:
                # this is where we crawl the source label:
                for lbl in source_labels:
                    child_node = self._crawl(lbl, node, follow_references)
                    node.children.append(child_node)
            self.target_to_node[label] = node
            self.library_to_nodes[node.artifact_def.library_path].append(node)
            self._store_if_leafnode(node)
            return node

    def _discover_dependencies(self, artifact_def, label):
        """
        Discovers the dependencies of the given artifact (==bazel target).

        This method returns a list of common.label.Label instances.
        """
        assert artifact_def is not None
        assert label is not None, "label is None for artifact %s" % artifact_def
        labels = ()
        if artifact_def.deps is not None:
            labels = [labelm.Label(lbl) for lbl in artifact_def.deps]
        if artifact_def.pom_generation_mode.query_dependency_attributes:
            labels += self._query_labels(artifact_def, label)
        return labels

    def _query_labels(self, artifact_def, label):
        """
        Delegates to bazel query to get the value of a bazel target's  "deps"
        and "runtime_deps" attributes. Returns an iterable of common.label.Label
        instances.
        """
        if not artifact_def.include_deps:
            return ()
        else:
            assert artifact_def.bazel_package is not None
            try:
                labels = bazel.query_java_library_deps_attributes(
                    self.workspace.repo_root_path,
                    label.canonical_form,
                    artifact_def.pom_generation_mode.dependency_attributes,
                    self.verbose)
                labels = [labelm.Label(lbl) for lbl in labels]
                return Crawler._remove_package_private_labels(labels, artifact_def)
            except Exception as e:
                msg = e.message if hasattr(e, "message") else type(e)
                raise Exception("Error while processing dependencies: %s %s caused by %s\nOne possible cause for this error is that the java_libary rule that builds the jar artifact is not the default bazel package target (same name as dir it lives in)" % (msg, artifact_def, repr(e)))

    @classmethod
    def _remove_package_private_labels(clazz, labels, owning_artifact_def):
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
                if owning_artifact_def.pom_generation_mode.produces_artifact:
                    continue
            updated_labels.append(label)
        return updated_labels

    @classmethod
    def _merge(clazz, label, artifact_def):
        assert isinstance(label, labelm.Label), "->%s" % label
        assert isinstance(artifact_def, buildpom.MavenArtifactDef), "->%s" % artifact_def
        pack_label = labelm.Label(label.package_path)
        if pack_label.target == artifact_def.bazel_target:
            # by default, the artifact def gets the default package target,
            # so ok to override it (maybe it should just be None...?)
            return label
        else:
            # the artifact def specifies a target that is not the package
            # default
            if label.is_default_target:
                # the label uses the default, so ok to overwrite
                return label.with_target(artifact_def.bazel_target)
            else:
                assert label.target == artifact_def.bazel_target, "conflicting target information: the artifact specifies [%s] but the current label is [%s]" % (artifact_def.bazel_target, label)
                return label
        raise AssertionError("we should not get here " + str(label))

    def _partition_and_filter_labels(self, labels, generation_strategy):
        """
        For the given lables, filters and partitions by source labels.
        Returns a tuple of source labels and dependencies.
        """
        source_labels = []
        deps = []
        for lbl in labels:
            lbl = self._filter_label(lbl)
            if lbl is None:
                continue
            artifact_def = None
            if lbl.is_source_ref:
                source_labels.append(lbl)
                artifact_def = self.workspace.parse_maven_artifact_def(lbl.package_path)
            dep = generation_strategy.load_dependency(lbl, artifact_def)
            deps.append(dep)
        return source_labels, deps

    def _filter_label(self, label):
        if label.canonical_form in self.workspace.excluded_dependency_labels:
            return None
        elif label.is_source_ref:
            for excluded_dependency_path in self.workspace.excluded_dependency_paths:
                if label.package_path.startswith(excluded_dependency_path):
                    return None
            artifact_def = self.workspace.parse_maven_artifact_def(label.package_path)
            if artifact_def is None:
                if bazel.is_never_link_dep(self.workspace.repo_root_path, label.canonical_form):
                    return None
                else:
                    # TODO
                    raise Exception("no BUILD.pom file in package [%s]" % label.package_path)
        return label

    def _store_if_leafnode(self, node):
        if len(node.children) == 0:
            self.leafnodes.append(node)

    def _any_artifact_requires_releasing(self, artifact_defs):
        """
        Returns whether at least one of the specified artifacts requires
        releasing, and its release_reason, as a tuple.
        """
        for art_def in artifact_defs:
            if art_def.requires_release:
                return (True, art_def.release_reason)
        return (False, None)

    def _print_debug_output(self, nodes, msg):
        """
        Debugging only - verbose output about the specified nodes.
        """
        self._print_debug_banner(msg)
        logger.raw("Top level nodes\n")
        for node in nodes:
            logger.raw("   %s\n" % node.artifact_def.bazel_package)
        logger.raw("\nCrawling children\n")
        leaf_nodes = []
        for node in nodes:
            self._debug_crawl_children(node, indent=0, leaf_nodes=leaf_nodes)
        logger.raw("\nLeaf nodes (without children)\n")
        for node in leaf_nodes:
            logger.raw("  %s\n" % node.artifact_def.bazel_package)
        logger.raw("\nCrawling parents (starting at leaf nodes)\n")
        for node in leaf_nodes:
            self._debug_crawl_parents(node, indent=0)
        logger.raw("\n")

    def _debug_crawl_children(self, node, indent, leaf_nodes):
        logger.raw("%s%s\n" % ("  "*indent, node.artifact_def.bazel_package))
        if len(node.children) == 0:
            if node.artifact_def.bazel_package not in [n.artifact_def.bazel_package for n in leaf_nodes]:
                leaf_nodes.append(node)
        else:
            for child in node.children:
                self._debug_crawl_children(child, indent+1, leaf_nodes)

    def _debug_crawl_parents(self, node, indent):
        logger.raw("%s%s\n" % ("  "*indent, node.artifact_def.bazel_package))
        for parent in node.parents:
            self._debug_crawl_parents(parent, indent+1)

    def _print_debug_banner(self, msg):
        sep = "========================================="
        logger.raw("%s\n" % sep)
        logger.raw("    %s\n" % msg)
        logger.raw("%s\n\n" % sep)

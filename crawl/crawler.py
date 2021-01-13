"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause


Crawls monorepo src dependencies and builds a DAG.
"""
from collections import defaultdict
from common import logger
from crawl import dependency
from crawl import bazel
from crawl import pom
from crawl import pomparser
from crawl import workspace
from crawl.releasereason import ReleaseReason
import difflib
import os


class Node:
    """
    A single node in the DAG, based on references in BUILD files.
    Each Bazel target gets its own Node instance. Typically, there is one 
    target per bazel package.
    """

    def __init__(self, parent, artifact_def, dependency):
        assert artifact_def is not None, "artifact_def cannot be None"
        assert dependency is not None, "dependency cannot be None"

        # the parent Nodes
        self.parents = [] if parent is None else [parent]
        # parsed metadata (BUILD.pom etc) files
        self.artifact_def = artifact_def
        # the dependency pointing to this target
        self.dependency = dependency
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
    Useful bits and pieces that are the outcome of crawling monorepo 
    BUILD files.
    """

    def __init__(self, pomgens, nodes, crawled_bazel_packages):

        # list of pom generators, for poms that need to be generated:
        self.pomgens = pomgens

        # list of root nodes
        self.nodes = nodes

        # set of Dependency instances, for all crawled bazel packages
        self.crawled_bazel_packages = crawled_bazel_packages


class Crawler:

    def __init__(self, workspace, pom_template, verbose=False):
        self.workspace = workspace
        self.pom_template = pom_template
        self.verbose = verbose # verbose logging
        self.package_to_artifact = {} # bazel package -> artifact def instance
        self.library_to_artifact = defaultdict(list) # library root path -> list of its artifact def instances
        self.library_to_nodes = defaultdict(list) # library root path -> list of its DAG Node instances
        self.target_to_node = {} # bazel target -> Node for that target
        self.target_to_dependencies = {} # bazel_target -> target's deps

        self.pomgens = [] # all pomgen instances
        self.leafnodes = [] # all leafnodes discovered while crawling

    def crawl(self, packages, follow_monorepo_references=True, force_release=False):
        """
        Crawls monorepo dependencies, starting at the specified packages.

        Builds up a DAG of Node instances based on the references in BUILD
        files.
        
        Arguments:

        follow_monorepo_references: 
            If False, this crawler will not crawl monorepo references, 
            effectively only processing the packages passed into this method

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
        nodes = self._crawl_packages(packages, follow_monorepo_references)


        # a library (LIBRARY.root) may have more than one artifact (Bazel
        # package with a BUILD.pom file). since we always release all artifacts
        # belonging to a library together, we need to make sure to gather all
        # artifacts for all libraries referenced. gathering artifacts may drag
        # in more artifacts in different libraries, so we continue until there
        # are no artifacts left to process
        if follow_monorepo_references:
            missing_packages = self._get_unprocessed_packages()
            while len(missing_packages) > 0:
                logger.info("Discovered additional packages %s" % missing_packages)
                nodes += self._crawl_packages(missing_packages, follow_monorepo_references)
                missing_packages = self._get_unprocessed_packages()



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


        # augment pom generators with deps discovered while crawling
        self._register_dependencies_with_pomgen_instances(target_to_transitive_closure_deps)


        # for each artifact, if its pom changed since the last release
        # (tracked by pom.xml.released), mark the artifact is requiring to be
        # released
        self._check_for_pom_changes()


        # figure out whether artifacts need to be released because a transitive
        # dependency needs to be released
        self._calculate_artifact_release_flag(force_release)


        # only pomgen instances for artifacts that need to be released are
        # included in the result
        result_pomgens = []
        for p in self.pomgens:
            if p.artifact_def.requires_release:
                result_pomgens.append(p)

        crawled_bazel_packages = self._get_crawled_packages_as_deps()

        return CrawlerResult(result_pomgens, nodes, crawled_bazel_packages)

    def _register_dependencies_with_pomgen_instances(self, target_to_transitive_closure_deps):
        """
        This method sets various dependency lists on all pomgen instances:

        - the direct dependencies that typically go into the generated pom
        - the transitive closure of the direct dependenices
        - the transitive closure of the library's dependencies
        """
        # register the direct dependencies
        for p in self.pomgens:
            target_key = self._get_target_key(p.bazel_package, p.dependency)
            dependencies = self.target_to_dependencies[target_key]
            p.register_dependencies(dependencies)

        # register the transitive closure of dependencies belonging to the
        # artifact
        deps = self._get_crawled_packages_as_deps()
        for p in self.pomgens:

            target_key = self._get_target_key(p.artifact_def.bazel_package, p.dependency)
            art_deps = target_to_transitive_closure_deps[target_key]
            p.register_dependencies_transitive_closure__artifact(art_deps)

        # register the transitive closure of dependencies belonging to the
        # library
        for p in self.pomgens:
            lib_deps = self._get_deps_transitive_closure_for_library(p.artifact_def.library_path, target_to_transitive_closure_deps)
            p.register_dependencies_transitive_closure__library(lib_deps)

    def _get_deps_transitive_closure_for_library(self, library_path,
                                                 target_to_transitive_closure_deps):
        all_deps = set()

        nodes = self.library_to_nodes[library_path]
        for n in nodes:
            target_key = self._get_target_key(n.artifact_def.bazel_package, n.dependency)
            all_deps.update(target_to_transitive_closure_deps[target_key])

        # also include every artifact that is part of this library
        # (we have already collected them above if they all reference each
        # other, but these references are not guaranteed)
        artifacts = self.library_to_artifact[library_path]
        for art_def in artifacts:
            all_deps.add(dependency.new_dep_from_maven_artifact_def(art_def, bazel_target=None))

        return all_deps

    def _get_crawled_packages_as_deps(self):
        deps = [dependency.new_dep_from_maven_artifact_def(art_def, bazel_target=None) for art_def in self.package_to_artifact.values()]
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
            if not library_path in processed_libraries:
                processed_libraries.add(library_path)
                all_library_packages = set(bazel.query_all_artifact_packages(self.workspace.repo_root_path, library_path))
                missing_packages += all_library_packages.difference(all_packages_already_processed)
        return missing_packages

    def _check_for_pom_changes(self):
        """
        For each artifact def not flagged as needing to be released, check 
        whether its current pom is different than the previously released pom.
        If the pom has changed, mark the artifact def as needing to be released.
        """

        for pomgen in self.pomgens:
            art_def = pomgen.artifact_def
            if not art_def.requires_release and art_def.released_pom_content is not None:
                current_pom = pomparser.format_for_comparison(pomgen.gen(pom.PomContentType.GOLDFILE))
                previous_pom = pomparser.format_for_comparison(art_def.released_pom_content)
                pom_changed = current_pom != previous_pom
                if pom_changed:
                    logger.debug("pom diff %s %s" % (art_def, art_def.bazel_package))
                    art_def.requires_release = True
                    art_def.release_reason = ReleaseReason.POM

                    # log pom diffs for debugging
                    diff = difflib.unified_diff(previous_pom.splitlines(True),
                                                current_pom.splitlines(True))
                    logger.raw(''.join(diff))
                    if self.verbose:
                        logger.debug("%s computed pom:" % art_def)
                        logger.raw(current_pom)
                        logger.debug("%s released pom:" % art_def)
                        logger.raw(previous_pom)


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
        package = node.artifact_def.bazel_package
        target_key = self._get_target_key(package, node.dependency)
        this_node_deps = self.target_to_dependencies[target_key]

        processed_deps = set() # to remove duplicate deps

        this_node_all_deps = list(this_node_deps)
        processed_deps.update(this_node_all_deps)

        # when encountering a duplicate dep, we keep this order:
        # 1) current deps from target
        # 2) previous transitive closure computation
        # 3) accumulated deps from child

        this_node_current_transitives = target_to_all_dependencies.get(target_key, ())
        this_node_all_deps += [d for d in this_node_current_transitives if d not in processed_deps]
        processed_deps.update(this_node_all_deps)

        this_node_all_deps += [d for d in accumulated_deps if d not in processed_deps]
        processed_deps.update(this_node_all_deps)

        target_to_all_dependencies[target_key] = this_node_all_deps

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
        package = node.artifact_def.bazel_package
        target_key = self._get_target_key(package, node.dependency)
        deps = self.target_to_dependencies[target_key]
        if node.artifact_def.pom_generation_mode.produces_artifact:
            if len(collected_dep_lists) > 0:
                deps = self.target_to_dependencies[target_key]
                collected_dep_lists.append(deps)
                deps = self._process_collected_dep_lists(collected_dep_lists)
                self.target_to_dependencies[target_key] = deps
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
                if not item in processed:
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
        logger.info("Processing transitive deps")
        for node in self.leafnodes:
            self._propagate_req_rel(node,
                                    transitive_dep_requires_release=False,
                                    force_release=force_release)

    def _propagate_req_rel(self, node, transitive_dep_requires_release, force_release):
        art_def = node.artifact_def
        library_path = art_def.library_path
        all_artifact_defs = self.library_to_artifact[library_path]
        assert len(all_artifact_defs) > 0, "expected some artifact defs"
        sibling_artifact_requires_release, sibling_release_reason = self._any_artifact_requires_releasing(all_artifact_defs)
        if (force_release or
            sibling_artifact_requires_release or
            transitive_dep_requires_release):
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
                                        force_release)

    def _crawl_packages(self, packages, follow_monorepo_references):
        """
        Returns a list of Node instances, one for each of the specified Bazel
        packages (directories). Each package must have a BUILD.pom file,
        as well as a LIBRARY.root file, either in the same directory as the 
        BUILD.pom file or in a parent directory (for libraries with more than
        one artifact).
        
        follow_monorepo_references: 
            If False, this method doesn't follow monorepo references.
        """
        nodes = []
        for package in packages:
            n = self._crawl(package, dep=None, parent_node=None, 
                            follow_monorepo_references=follow_monorepo_references)
            nodes.append(n)
        return nodes
    
    def _crawl(self, package, dep, parent_node, follow_monorepo_references):
        """
        For the specified package, crawl monorepo dependencies, unless
        follow_monorepo_references is False.

        The dependency instance is the dependency pointing at this package.

        Returns a Node instance for the crawled package.
        """
        target_key = self._get_target_key(package, dep)
        if target_key in self.target_to_node:
            # if we have already processed this target, we can re-use the
            # children we discovered previously
            # for example: A -> B -> C is how we found B, and now we got here
            # through another path: A -> Z -> B -> C
            # the parent is different, but the children have to be the same
            cached_node = self.target_to_node[target_key]
            node = Node(parent_node, cached_node.artifact_def, 
                        cached_node.dependency)
            node.children = cached_node.children
            # also add the new parent to the cached_node - this is important
            # because we have logic that traverses the nodes from children to
            # parent nodes
            cached_node.parents.append(node)
            self.library_to_nodes[node.artifact_def.library_path].append(node)
            self._store_if_leafnode(node)
            if self.verbose:
                logger.debug("Skipping re-crawling of artifact [%s] with target key [%s] because it has already happened" % (cached_node.artifact_def, target_key))
            return node
        else:
            logger.info("Processing [%s]" % target_key)
            artifact_def = self.workspace.parse_maven_artifact_def(package)

            if artifact_def is None:
                raise Exception("No artifact defined at package %s" % package)
            
            self._validate_default_target_dep(parent_node, dep, artifact_def)

            self.package_to_artifact[package] = artifact_def
            self.library_to_artifact[artifact_def.library_path].append(artifact_def)
            pomgen = self._get_pom_generator(artifact_def, dep)
            self.pomgens.append(pomgen)
            source_deps, ext_deps, all_deps = pomgen.process_dependencies()
            self.target_to_dependencies[target_key] = all_deps
            if self.verbose:
                logger.debug("Determined deps for artifact: [%s] with target key [%s]" % (artifact_def, target_key))
                logger.debug("Source deps: %s" % "\n".join([str(d) for d in source_deps]))
                logger.debug("Ext deps: %s" % "\n".join([str(d) for d in ext_deps]))
                logger.debug("All deps: %s" % "\n".join([str(d) for d in all_deps]))
            node = Node(parent_node, artifact_def, pomgen.dependency)
            if follow_monorepo_references:
                # crawl monorepo dependencies
                for source_dep in source_deps:
                    child_node = self._crawl(source_dep.bazel_package,
                                             source_dep, node, 
                                             follow_monorepo_references)
                    node.children.append(child_node)
            self.target_to_node[target_key] = node
            self.library_to_nodes[node.artifact_def.library_path].append(node)
            self._store_if_leafnode(node)
            return node

    def _validate_default_target_dep(self, parent_node, dep, artifact_def):
        if dep is not None:
            if artifact_def.pom_generation_mode.produces_artifact:
                # if the current bazel target produces an artifact 
                # (pom/jar that goes to Nexus), validate that the BUILD 
                # file pointing at this target uses the default bazel 
                # package target 
                # this is a current pomgen requirement: 
                # 1 bazel package produces one artifact, named after the 
                # bazel package
                dflt_package_name = os.path.basename(artifact_def.bazel_package)
                if dep.bazel_target != dflt_package_name:
                    raise Exception("Non default-package references are only supported to non-artifact producing packages: [%s] can only reference [%s], [%s:%s] is not allowed" % (parent_node.artifact_def.bazel_package, artifact_def.bazel_package, artifact_def.bazel_package, dep.bazel_target))

    def _get_pom_generator(self, artifact_def, dep):
        if dep is None:
            # make a real dependency instance here so we can pass it along
            # into the pom generator
            dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        return pom.get_pom_generator(self.workspace, 
                                     self.pom_template, artifact_def,
                                     dep)

    @classmethod
    def _get_target_key(clazz, package, dep):
        if dep is None:
            target = os.path.basename(package)
        else:
            target = dep.bazel_target
        assert target is not None, "Target is None for dep %s" % dep
        return "%s:%s" % (package, target)

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

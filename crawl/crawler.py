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
    Each Bazel package with a BUILD.pom file gets its own Node instance.
    """

    def __init__(self, artifact_def, parent):
        assert artifact_def is not None, "artifact_def cannot be None"
        self.artifact_def = artifact_def # parsed metadata (BUILD.pom etc) files
        self.parent = parent             # the parent Node, None if no parent
        self.children = []               # all direct child nodes

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
    def __init__(self, workspace, pom_template):
        self.workspace = workspace
        self.pom_template = pom_template
        self.package_to_artifact = {} # bazel package -> artifact def instance
        self.library_to_artifact = defaultdict(list) # library root path -> list of its artifact def instances
        self.library_to_nodes = defaultdict(list) # library root path -> list of its DAG Node instances
        self.package_to_childnodes = defaultdict(list) # bazel package -> list of DAG child Node instances

        self.pomgens = [] # pomgen instances for all packages
        self.leafnodes = [] # all leafnodes discovered while crawling

        self.crawled_external_dependencies = set() # all external dependencies discovered while crawling around

    def crawl(self, packages, follow_monorepo_references=True, force=False):
        """
        Crawls monorepo dependencies, starting at the specified packages.

        Builds up a DAG of Node instances based on the references in BUILD
        files.
        
        Arguments:

        follow_monorepo_references: 
            If False, this crawler will not crawl monorepo references, 
            effectively only processing the packages passed into this method

            This is typically only used for debugging.

        force:
            Generate poms for all artifacts, even when they do not need to
            be released

        Returns a CrawlerResult instance.
        """


        # first we build the initial DAG, by starting a one or more packages
        # and traversing references expressed in BUILD files, specifically
        # deps and runtime deps of the single java_library target.
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
            logger.info("Looking for additional packages ...")
            missing_packages = self._get_unprocessed_packages()
            while len(missing_packages) > 0:
                logger.info("Discovered missing packages %s" % missing_packages)
                nodes += self._crawl_packages(missing_packages, follow_monorepo_references)
                missing_packages = self._get_unprocessed_packages()


        # augment pom generators with deps discovered while crawling
        crawled_bazel_packages = set([dependency.new_dep_from_maven_artifact_def(a) for a in list(self.package_to_artifact.values())])
        for p in self.pomgens:
            p.register_dependencies(crawled_bazel_packages, 
                                    self.crawled_external_dependencies)


        # for each artifact, if its pom changed since the last release
        # (tracked by pom.xml.released), mark the artifact is requiring to be
        # released
        self._check_for_pom_changes()


        # figure out whether artifacts need to be released because a transitive
        # dependency needs to be released
        self._calculate_artifact_release_flag(force)


        # only pomgen instances for artifacts that need to be released are
        # included in the result
        pomgens = [p for p in self.pomgens if p.artifact_def.requires_release]


        return CrawlerResult(pomgens, nodes, crawled_bazel_packages)

    def _get_unprocessed_packages(self):
        """
        For each crawled library, ensure we have included all its packages (each
        package with a BUILD.pom file is a single maven artifact)
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
                current_pom = pomparser.pretty_print(pomgen.gen(pom.PomContentType.GOLDFILE))
                previous_pom = pomparser.pretty_print(art_def.released_pom_content)
                pom_changed = current_pom != previous_pom
                if pom_changed:
                    logger.debug("pom change for %s" % art_def)
                    art_def.requires_release = True
                    art_def.release_reason = ReleaseReason.POM

                    # log pom diffs for debugging
                    diff = difflib.unified_diff(previous_pom.splitlines(True),
                                                current_pom.splitlines(True))
                    logger.raw(''.join(diff))

    def _calculate_artifact_release_flag(self, force_release):
        """
        Given libraries A->B->C->D, if only C changed, we need to also mark
        the reverse trasitive deps as having changed, so that we end up
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
                if not artifact_def.requires_release:
                    artifact_def.requires_release = True
                    if sibling_artifact_requires_release:
                        artifact_def.release_reason = sibling_release_reason
                    elif transitive_dep_requires_release:
                        artifact_def.release_reason = ReleaseReason.TRANSITIVE
                    else:
                        artifact_def.release_reason = ReleaseReason.FORCE
                    updated_artifact_defs.append(artifact_def)
            if len(updated_artifact_defs) > 0:
                logger.info("Marked artifacts requiring releasing for library [%s]: %s" % (library_path,[str(a) for a in updated_artifact_defs]))

        # process all artifact nodes belonging to the current library, 
        # otherwise we may miss some references to other libraries
        all_artifact_nodes = self.library_to_nodes[library_path]
        for n in all_artifact_nodes:
            if n.parent is not None:
                if n.parent.artifact_def.library_path == n.artifact_def.library_path:
                    # no need to crawl within the same library
                    continue
                if n.artifact_def.requires_release and not force_release:
                    transitive_dep_requires_release = True
                self._propagate_req_rel(n.parent,
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
        return [self._crawl(p, None, follow_monorepo_references) for p in packages]
    
    def _crawl(self, package, parent_node, follow_monorepo_references):
        """
        For the specified package, crawl monorepo dependencies, unless
        follow_monorepo_references is False.

        Returns a Node instance for the crawled package.
        """
        
        if package in self.package_to_childnodes:
            # if we have already processed this package, we can re-use the
            # children we discovered previously
            # for example: A -> B -> C is how we found B, and now we got here
            # through another path: A -> Z -> B -> C
            # the parent is different, but the children have to be the same
            node = Node(self.package_to_artifact[package], parent_node)
            node.children = self.package_to_childnodes[package]
            self.library_to_nodes[node.artifact_def.library_path].append(node)
            self._store_leafnode(node)
            return node
        else:
            logger.info("Processing %s" % package)
            artifact_def = self.workspace.parse_maven_artifact_def(package)
            node = Node(artifact_def, parent_node)
            self.package_to_artifact[package] = artifact_def
            self.library_to_artifact[artifact_def.library_path].append(artifact_def)
            pomgen = pom.get_pom_generator(self.workspace, self.pom_template, artifact_def)
            self.pomgens.append(pomgen)
            source_deps, ext_deps = pomgen.process_dependencies()
            self.crawled_external_dependencies.update(ext_deps)
            child_packages = [dep.bazel_package for dep in source_deps]
            if follow_monorepo_references:
                for child_package in child_packages:
                    child_node = self._crawl(child_package, node,
                                             follow_monorepo_references)
                    node.children.append(child_node)
            self.package_to_childnodes[package] = node.children
            self.library_to_nodes[node.artifact_def.library_path].append(node)
            self._store_leafnode(node)
            return node

    def _store_leafnode(self, node):
        if len(node.children) == 0:
            self.leafnodes.append(node)

    def _any_artifact_requires_releasing(self, artifact_defs):
        """
        Returns whether at least one artifact requires releasing, and the
        release_reason, as a tuple.
        """
        requires_release = False
        for art_def in artifact_defs:
            if art_def.requires_release:
                requires_release = True
                if art_def.release_reason in (ReleaseReason.ARTIFACT, ReleaseReason.FIRST):
                    return (True, art_def.release_reason)
        if requires_release:
            return (True, ReleaseReason.POM)
        return (False, None)


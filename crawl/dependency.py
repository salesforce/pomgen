"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from functools import total_ordering
import os


@total_ordering
class AbstractDependency(object):
    """

    Required/always set:

    group_id: the maven artifact groupId of this depdendency.

    artifact_id: the maven artifact id (artifactId) of this depdendency.

    version: the maven artifact version of this depdendency.

    external: True -> this dependency references a Nexus artifact 
              (which could be a previously uploaded monorepo artifact)
              False -> this is a monorepo source dependency

    references_artifact: True -> this dependency references another maven
                         artifact
                         False -> this is a "traversal only" dependency

    bazel_buildable: True -> this dependency is built by bazel (-> this
                     dependency repesents a jar built by bazel)
                     False -> this is an external dependency or a pom artifact
                     or something else that bazel cannot build


    Optional/may be None:

    classifier: the maven artifact classifier
    packaging: the maven artifact packaging
    scope: the maven scope of the dependency
    
    bazel_package: The bazel package this dependency lives in, None for 
        artifacts that are not built out of the monorepo (for example Guava).

    bazel_target: If bazel_packge is not None, the specific target for this
        dependency.

    """
    def __init__(self, group_id, artifact_id,
                 classifier=None, packaging=None, scope=None):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.classifier = classifier
        self.packaging = "jar" if packaging is None else packaging
        self.scope = scope

    @property
    def maven_coordinates_name(self):
        """
        The Maven "coords" representation for this dependency, EXCLUDING the
        version.
        """
        c = "%s:%s" % (self.group_id, self.artifact_id)
        if self.classifier is None:
            if self.packaging not in (None, "jar"):
                c = "%s:%s" % (c, self.packaging)
        else:
            pack = "jar" if self.packaging is None else self.packaging
            c = "%s:%s:%s" % (c, pack, self.classifier)
        return c

    @property
    def bazel_label_name(self):
        """
        The bazel label used to reference this dependency.
        TODO this isn't implemented consistently in subclasses - it is only
        implemented/used by clients of ThirdPartyDependency
        """
        return None

    @property    
    def unqualified_bazel_label_name(self):
        """
        If the bazel_label_name starts with a repository name (== maven install
        rule name), using the syntax "@<repo name>", returns the label without
        the repository name.
        
        Note that this method is implemented in terms of bazel_label_name,
        and therefore it is not implemented in subclasses.
        """
        label = self.bazel_label_name
        if label is None:
            return None
        if label.startswith("@"):
            i = label.index("//")
            label = label[i+2:]
            if label.startswith(":"):
                label = label[1:]
        return label

    @property
    def version(self):
        raise Exception("must be implemented in subclass")

    @property
    def external(self):
        raise Exception("must be implemented in subclass")

    @property
    def bazel_package(self):
        raise Exception("must be implemented in subclass")

    @property
    def bazel_target(self):
        raise Exception("must be implemented in subclass")

    @property
    def references_artifact(self):
        raise Exception("must be implemented in subclass")

    @property
    def bazel_buildable(self):
        raise Exception("must be implemented in subclass")

    def __hash__(self):
        return hash((self.group_id, self.artifact_id, self.classifier, self.packaging))

    def __eq__(self, other):
        return (self.group_id == other.group_id and
                self.artifact_id == other.artifact_id and
                self.classifier == other.classifier and
                self.packaging == other.packaging)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if self.bazel_package is None:
            # self is a 3rd party dep
            if other.bazel_package is None:
                # other is also a 3rd party dep, compare attributes:
                # group_id, artifact_id, classifier, packaging, scope
                my_classifier = "" if self.classifier is None else self.classifier
                other_classifier = "" if other.classifier is None else other.classifier
                my_packaging = "" if self.packaging is None else self.packaging
                other_packaging = "" if other.packaging is None else other.packaging
                my_scope = "" if self.scope is None else self.scope
                other_scope = "" if other.scope is None else other.scope
                return (self.group_id,
                        self.artifact_id,
                        my_classifier,
                        my_packaging,
                        my_scope) < (other.group_id,
                                     other.artifact_id,
                                     other_classifier,
                                     other_packaging,
                                     other_scope)
            else:
                # other is a monorepo dep, 3rd party goes last
                return False
        else:
            # self is a monorepo dep
            if other.bazel_package is None:
                # other is a 3rd party dep, monorepo goes first
                return True
            else:
                # other is also a monorepo dep, compare based on name
                return (self.group_id, self.artifact_id) < (other.group_id, other.artifact_id)

    def __str__(self):
        if self.references_artifact:
            return self.maven_coordinates_name
        else:
            return "%s (ref)" % self.bazel_package

    def __repr__(self):
        return self.__str__()


class ThirdPartyDependency(AbstractDependency):

    def __init__(self, maven_install_name, group_id, artifact_id, version,
                 classifier=None, packaging=None, scope=None):
        super(ThirdPartyDependency, self).__init__(group_id, artifact_id,
                                                   classifier, packaging, scope)
        self._version = version
        if maven_install_name is not None and maven_install_name.startswith("@"):
            maven_install_name = maven_install_name[1:]
        self._maven_install_name = maven_install_name

    @property
    def external(self):
        return True

    @property
    def bazel_package(self):
        return None

    @property
    def bazel_target(self):
        return None

    @property
    def references_artifact(self):
        return True

    @property
    def version(self):
        return self._version

    @property
    def bazel_label_name(self):
        name = self._bzl_artifact_name()
        if self._maven_install_name is not None:
            name = "@%s//:%s" % (self._maven_install_name, name)
        return name

    @property
    def bazel_buildable(self):
        return False

    def _bzl_artifact_name(self):
        """
        The Maven artifact name without its repo prefix.
        """
        return self._normalize("%s_%s%s%s" %
          (self.group_id,
           self.artifact_id,
           "" if self.packaging in (None, "jar") else "_" + self.packaging,
           "" if self.classifier is None else "_" + self.classifier))

    def _normalize(self, n):
        n = n.replace('-', '_')
        n = n.replace('.', '_')
        return n

class MonorepoDependency(AbstractDependency):

    def __init__(self, artifact_def, bazel_target):
        super(MonorepoDependency, self).__init__(artifact_def.group_id,
                                                 artifact_def.artifact_id)
        self._artifact_def = artifact_def
        self._bazel_target = MonorepoDependency._init_target(
            artifact_def.bazel_package, bazel_target)

    @property
    def version(self):
        use_released = self._use_previously_released_artifact()
        return self._artifact_def.released_version if use_released else self._artifact_def.version

    @property
    def external(self):
        return True if self._use_previously_released_artifact() else False

    @property
    def bazel_package(self):
        return self._artifact_def.bazel_package

    @property
    def bazel_target(self):
        return self._bazel_target

    @property
    def bazel_buildable(self):
        pom_template = self._artifact_def.custom_pom_template_content
        return self._artifact_def.pom_generation_mode.bazel_produced_artifact(pom_template)

    @property
    def references_artifact(self):
        return self._artifact_def.pom_generation_mode.produces_artifact

    @classmethod
    def _init_target(clazz, bazel_package, bazel_target):
        if bazel_target is not None:
            return bazel_target
        if bazel_package is not None:
            return os.path.basename(bazel_package)
        return None

    def _use_previously_released_artifact(self):
        if self._artifact_def.requires_release is not None:
            # better to be explicit here: requires_release has been set
            if self._artifact_def.requires_release == False:
                return True
        return False


def new_dep_from_maven_art_str(maven_artifact_str, name):
    num_coordinates = maven_artifact_str.count(':') + 1
    classifier = None
    packaging = None
    try:
        if num_coordinates == 3:
            # com.google.guava:guava:20.0
            group_id, artifact_id, version = maven_artifact_str.split(':')
        elif num_coordinates == 4:
            # com.squareup:javapoet:jar:1.11.1
            group_id, artifact_id, packaging, version = maven_artifact_str.split(':')            
        else:
            # com.grail.servicelibs:dynamic-keystore-impl:jar:tests:2.0.39
            group_id, artifact_id, packaging, classifier, version = maven_artifact_str.split(':')
    except Exception as e:
        raise Exception ("cannot parse artifact specification [%s]" % maven_artifact_str) from e

    version = version.strip()
    if len(version) == 0:
        # version should always be specified for external dependencies
        raise Exception("invalid version in artifact [%s]" % maven_artifact_str)

    return ThirdPartyDependency(name, group_id, artifact_id, version,
                                classifier, packaging)


def new_dep_from_maven_artifact_def(artifact_def, bazel_target=None):
    if bazel_target is not None:
        assert len(bazel_target) > 0, "bazel target must not be empty for artifact def %s" % artifact_def.bazel_package
    return MonorepoDependency(artifact_def, bazel_target)


"""
Dummy version for dependencies instances that only have significant
group/artifact ids (such as the dependencies used to represent exclusions)
"""
GA_DUMMY_DEP_VERSION = "-1"


"""
Dependency instance with artifact and group ids set to "*".
"""
EXCLUDE_ALL_PLACEHOLDER_DEP = new_dep_from_maven_art_str(
    "*:*:%s" % GA_DUMMY_DEP_VERSION, "dummy_placeholder_label")

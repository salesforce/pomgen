"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import common.label as label
import generate
from functools import total_ordering
 

@total_ordering
class AbstractJarDependency(generate.AbstractDependency):
    """
    Required/always set:

    group_id: the maven artifact groupId of this depdendency.

    artifact_id: the maven artifact id (artifactId) of this depdendency.

    version: the maven artifact version of this depdendency.
    """
    def __init__(self, label, group_id, artifact_id,
                 packaging=None, classifier=None, scope=None):
        self._label = label
        self._artifact_id = artifact_id
        self._group_id = group_id
        self._packaging = "jar" if packaging is None else packaging
        self._classifier = classifier
        self._scope = scope

    @property
    def artifact_id(self):
        return self._artifact_id

    @property
    def group_id(self):
        return self._group_id

    @property
    def packaging(self):
        return self._packaging

    @property
    def classifier(self):
        return self._classifier

    @property
    def scope(self):
        return self._scope

    @property
    def label(self):
        return self._label

    @property
    def version(self):
        raise Exception("must be implemented in subclass")

    @property
    def native_repr(self):
        c = "%s:%s" % (self._group_id, self._artifact_id)
        if self._classifier is None:
            if self._packaging != "jar":
                c = "%s:%s" % (c, self.packaging)
        else:
            c = "%s:%s:%s" % (c, self._packaging, self._classifier)
        return "%s:%s" % (c, self.version)

    # note that hash/eq/lt etc don't use the version because
    # the version can change based on the value of requires_release
    # we need to check whether we can create dependency instances after
    # the value of requires release is known so we can make this more consistent
    def __hash__(self):
        return hash((self._group_id, self._artifact_id, self._classifier, self._packaging))

    def __eq__(self, other):
        return (self._group_id == other._group_id and
                self._artifact_id == other._artifact_id and
                self._classifier == other._classifier and
                self._packaging == other._packaging)

    def __ne__(self, other):
        return self != other

    def __lt__(self, other):
        if not self.label.is_source_ref:
            # self is a 3rd party dep
            if not other.label.is_source_ref:
                # other is also a 3rd party dep, compare attributes:
                # group_id, artifact_id, classifier, packaging, scope
                my_classifier = "" if self._classifier is None else self._classifier
                other_classifier = "" if other._classifier is None else other._classifier
                my_packaging = "" if self._packaging is None else self._packaging
                other_packaging = "" if other._packaging is None else other._packaging
                my_scope = "" if self._scope is None else self._scope
                other_scope = "" if other._scope is None else other._scope
                return (self._group_id,
                        self._artifact_id,
                        my_classifier,
                        my_packaging,
                        my_scope) < (other._group_id,
                                     other._artifact_id,
                                     other_classifier,
                                     other_packaging,
                                     other_scope)
            else:
                # other is a repository dep, 3rd party goes last
                return False
        else:
            # self is a repository dep
            if not other.label.is_source_ref:
                # other is a 3rd party dep, repository goes first
                return True
            else:
                # other is also a repository dep, compare based on name
                return (self.group_id, self.artifact_id) < (other.group_id, other.artifact_id)

    def __str__(self):
        s = "%s %s" % (self.native_repr, "(local)" if self.label.is_source_ref else "")
        return s.strip()

    def __repr__(self):
        return self.__str__()


class ExternalDependency(AbstractJarDependency):

    def __init__(self, maven_install_name, group_id, artifact_id, version,
                 packaging=None, classifier=None, scope=None):
        label = ExternalDependency._build_label(
            group_id, artifact_id, packaging, classifier, maven_install_name)
        super().__init__(label, group_id, artifact_id, packaging, classifier, scope)
        self._version = version
        self._maven_install_name = maven_install_name

    @property
    def version(self):
        return self._version

    @property
    def label(self):
        return self._label

    @classmethod
    def _build_label(clazz, group_id, artifact_id, packaging, classifier, repo_name):
        label_str = ExternalDependency._normalize("%s_%s%s%s" %
          (group_id, artifact_id,
           "" if packaging in (None, "jar") else "_" + packaging,
           "" if classifier is None else "_" + classifier))

        if repo_name is None:
            label_str = "//:%s" % label_str
        else:
            label_str = "%s//:%s" % (repo_name, label_str)
            if not label_str.startswith("@"):
                label_str = "@%s" % label_str
        return label.Label(label_str)

    @classmethod
    def _normalize(clazz, n):
        n = n.replace('-', '_')
        n = n.replace('.', '_')
        return n


class SourceDependency(AbstractJarDependency):

    def __init__(self, artifact_def):
        lbl = label.Label(artifact_def.bazel_package)
        if artifact_def.bazel_target is not None:
            lbl = lbl.with_target(artifact_def.bazel_target)
        super().__init__(lbl, artifact_def.group_id, artifact_def.artifact_id)
        self._artifact_def = artifact_def

    @property
    def version(self):
        use_released = self._use_previously_released_artifact()
        return self._artifact_def.released_version if use_released else self._artifact_def.version

    def _use_previously_released_artifact(self):
        if self._artifact_def.requires_release is not None:
            # better to be explicit here: requires_release has been set
            if self._artifact_def.requires_release == False: # noqa: E712
                return True
        return False


def new_dep_from_maven_art_str(maven_artifact_str, maven_install_name, scope=None):
    assert maven_artifact_str is not None
    assert maven_install_name is not None
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
    assert len(version) > 0, "Invalid version in artifact [%s]" % maven_artifact_str

    return ExternalDependency(maven_install_name, group_id, artifact_id, version,
                              packaging, classifier, scope)


def new_dep_from_maven_artifact_def(artifact_def):
    return SourceDependency(artifact_def)


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

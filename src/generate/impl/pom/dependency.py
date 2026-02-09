"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

import common.label as labelm
import generate
from functools import total_ordering
 

@total_ordering
# TODO rename file
class PomDependency(generate.AbstractDependency):

    @classmethod
    def init_with_artifact_def(clazz, artifact_def):
        assert artifact_def is not None
        label = None
        return PomDependency(label, artifact_def)

    @classmethod
    def init_with_components(clazz, group_id, artifact_id, version, packaging,
                             classifier, scope, maven_install_name,
                             version_must_be_set):
        if version_must_be_set:
            assert version is not None
        label = _build_ext_dep_label(group_id, artifact_id, packaging, classifier, maven_install_name)
        artifact_def = None
        return PomDependency(label, artifact_def, group_id, artifact_id,
                             version, packaging, classifier, scope)

    # private
    def __init__(self, label, artifact_def, group_id=None, artifact_id=None,
                 version=None, packaging=None, classifier=None, scope=None):
        super().__init__(label, artifact_def, artifact_id, version)
        if artifact_def is None:
            assert group_id is not None
            self._group_id = group_id
        else:
            assert group_id is None
            self._group_id = artifact_def.group_id
        self._packaging = "jar" if packaging is None else packaging
        self._classifier = classifier
        self._scope = scope

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
        if self is other:
            return True
        return (self._group_id == other._group_id and
                self._artifact_id == other._artifact_id and
                self._classifier == other._classifier and
                self._packaging == other._packaging)

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
                return (self._group_id, self._artifact_id) < (other._group_id, other._artifact_id)


def _build_ext_dep_label(group_id, artifact_id, packaging, classifier, maven_install_name):
    label_str = _normalize("%s_%s%s%s" %
      (group_id, artifact_id,
       "" if packaging in (None, "jar") else "_" + packaging,
       "" if classifier is None else "_" + classifier))

    if  maven_install_name is None:
        label_str = "//:%s" % label_str
    else:
        label_str = "%s//:%s" % (maven_install_name, label_str)
        if not label_str.startswith("@"):
            label_str = "@%s" % label_str
    return labelm.Label(label_str)


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

    return PomDependency.init_with_components(
        group_id, artifact_id, version,
        packaging, classifier, scope,
        maven_install_name,
        version_must_be_set=True)


def new_dep_from_maven_artifact_def(artifact_def):
    return PomDependency.init_with_artifact_def(artifact_def)


def _normalize(n):
    n = n.replace('-', '_')
    n = n.replace('.', '_')
    return n


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

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl.buildpom import MavenArtifactDef
from crawl import dependency
from crawl.crawler import Node
from crawl.releasereason import ReleaseReason
import crawl.libaggregator
import unittest

class LibAggregatorTest(unittest.TestCase):

    def test_single_lib__requires_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=True)
        a2 = self._create_library_artifact_node("g1", "a2", "1.0.0", "mylib",
                                                requires_release=True)
        a3 = self._create_library_artifact_node("g1", "a3", "1.0.0", "mylib",
                                                requires_release=True)

        lib_nodes = crawl.libaggregator.get_libraries_to_release([a1, a2, a3])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(0, len(lib_nodes[0].children))
        self.assertEqual("1.0.0-SNAPSHOT", lib_nodes[0].version)
        self.assertEqual(lib_nodes[0].library_path, "mylib")
        self.assertTrue(lib_nodes[0].requires_release)
        self.assertEqual(ReleaseReason.ARTIFACT, lib_nodes[0].release_reason)

    def test_single_lib__does_not_require_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=False)
        a2 = self._create_library_artifact_node("g1", "a2", "1.0.0", "mylib",
                                                requires_release=False)
        a3 = self._create_library_artifact_node("g1", "a3", "1.0.0", "mylib",
                                                requires_release=False)

        lib_nodes = crawl.libaggregator.get_libraries_to_release([a1, a2, a3])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(0, len(lib_nodes[0].children))
        self.assertEqual("1.0.0", lib_nodes[0].version)
        self.assertEqual(lib_nodes[0].library_path, "mylib")
        self.assertFalse(lib_nodes[0].requires_release)
        self.assertIsNone(lib_nodes[0].release_reason)

    def test_two_libraries(self):
        """
        2 libraries, mylib and mylib2, with an artifact in mylib, g1:a2, 
        referencing an artifact in mylib2, g2:a1.
        """
        l1a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                  requires_release=True)
        l1a2 = self._create_library_artifact_node("g1", "a2", "1.0.0", "mylib",
                                                  requires_release=True)
        l2a1 = self._create_library_artifact_node("g2", "a1", "2.0.0", "mylib2",
                                                  requires_release=True)
        l2a2 = self._create_library_artifact_node("g2", "a2", "2.0.0", "mylib2",
                                                  requires_release=True)

        l1a2.children = [l2a1]
        l2a1.parent = l1a2        
        lib_nodes = crawl.libaggregator.get_libraries_to_release([l1a1, l1a2])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(1, len(lib_nodes[0].children))
        lib = lib_nodes[0]
        self.assertEqual("1.0.0-SNAPSHOT", lib.version)
        self.assertEqual(lib.library_path, "mylib")
        self.assertTrue(lib.requires_release)
        self.assertEqual(ReleaseReason.ARTIFACT, lib.release_reason)

        lib = lib.children[0]
        self.assertEqual("2.0.0-SNAPSHOT", lib.version)
        self.assertEqual(lib.library_path, "mylib2")
        self.assertTrue(lib.requires_release)
        self.assertEqual(ReleaseReason.ARTIFACT, lib.release_reason)        

    def test_release_reason_precedence__first(self):
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.FORCE))

    def test_release_reason_precedence__artifact(self):
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.FORCE))

    def test_release_reason_precedence__transitive(self):
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.TRANSITIVE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.FORCE))

    def test_release_reason_precedence__pom(self):
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.FORCE))
        
    def test_release_reason_precedence__force(self):
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FORCE, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FORCE, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FORCE, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FORCE, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FORCE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FORCE, ReleaseReason.FORCE))

    def _create_library_artifact_node(self, group_id, artifact_id, version,
                                      library_path, requires_release,
                                      release_reason=None):
        dev_version = version + "-SNAPSHOT"
        released_version = version
        if requires_release and release_reason is None:
            release_reason = ReleaseReason.ARTIFACT
        artifact_def = MavenArtifactDef(group_id, artifact_id, dev_version,
                                        released_version=released_version,
                                        library_path=library_path,
                                        requires_release=requires_release)
        artifact_def.release_reason = release_reason
        dep = dependency.new_dep_from_maven_artifact_def(artifact_def)
        return Node(parent=None, artifact_def=artifact_def, dependency=dep)

if __name__ == '__main__':
    unittest.main()

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


from common import label
from crawl.buildpom import MavenArtifactDef
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

    def test_pretty_print__single_lib__requires_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=True,
                                                release_reason=ReleaseReason.FIRST)

        lib_nodes = crawl.libaggregator.get_libraries_to_release([a1,])
        pretty_output = lib_nodes[0].pretty_print()

        self.assertIn("mylib ++ 1.0.0", pretty_output)
        self.assertIn("++ artifact has never been released", pretty_output)

    def test_pretty_print__single_lib__does_not_require_release(self):
        """
        Make sure the pretty message honors requires_release, instead of
        just checking wether release_reason is None or not.
        """
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=False,
                                                release_reason=ReleaseReason.FIRST)

        lib_nodes = crawl.libaggregator.get_libraries_to_release([a1,])
        pretty_output = lib_nodes[0].pretty_print()

        self.assertIn("mylib - 1.0.0", pretty_output)
        self.assertIn("- no changes to release", pretty_output)

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

    def test_release_reason_precedence__always(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ALWAYS, ReleaseReason.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__first(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.FIRST, ReleaseReason.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__artifact(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.ARTIFACT, ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__pom(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.POM, ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__transitive(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(ReleaseReason.ARTIFACT, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.POM, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.TRANSITIVE, crawl.libaggregator._get_lib_release_reason(ReleaseReason.TRANSITIVE, ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__uncommitted(self):
        self.assertEqual(ReleaseReason.ALWAYS, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.ALWAYS))
        self.assertEqual(ReleaseReason.FIRST, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.FIRST))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.ARTIFACT))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.POM))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.TRANSITIVE))
        self.assertEqual(ReleaseReason.UNCOMMITTED_CHANGES, crawl.libaggregator._get_lib_release_reason(ReleaseReason.UNCOMMITTED_CHANGES, ReleaseReason.UNCOMMITTED_CHANGES))

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
                                        requires_release=requires_release,
                                        bazel_target="t1")
        artifact_def.release_reason = release_reason
        return Node(parent=None, artifact_def=artifact_def,
                    label=label.Label(library_path))


if __name__ == '__main__':
    unittest.main()

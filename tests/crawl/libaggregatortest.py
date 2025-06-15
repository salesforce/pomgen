"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import common.label as label
import crawl.buildpom as buildpom
import crawl.crawler as crawler
import crawl.libaggregator as libaggregator
import crawl.releasereason as rr
import unittest


class LibAggregatorTest(unittest.TestCase):

    def test_single_lib__requires_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=True)
        a2 = self._create_library_artifact_node("g1", "a2", "1.0.0", "mylib",
                                                requires_release=True)
        a3 = self._create_library_artifact_node("g1", "a3", "1.0.0", "mylib",
                                                requires_release=True)

        lib_nodes = libaggregator.get_libraries_to_release([a1, a2, a3])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(0, len(lib_nodes[0].children))
        self.assertEqual("1.0.0-SNAPSHOT", lib_nodes[0].version)
        self.assertEqual(lib_nodes[0].library_path, "mylib")
        self.assertTrue(lib_nodes[0].requires_release)
        self.assertEqual(rr.ReleaseReason.ARTIFACT, lib_nodes[0].release_reason)

    def test_single_lib__does_not_require_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=False)
        a2 = self._create_library_artifact_node("g1", "a2", "1.0.0", "mylib",
                                                requires_release=False)
        a3 = self._create_library_artifact_node("g1", "a3", "1.0.0", "mylib",
                                                requires_release=False)

        lib_nodes = libaggregator.get_libraries_to_release([a1, a2, a3])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(0, len(lib_nodes[0].children))
        self.assertEqual("1.0.0", lib_nodes[0].version)
        self.assertEqual(lib_nodes[0].library_path, "mylib")
        self.assertFalse(lib_nodes[0].requires_release)
        self.assertIsNone(lib_nodes[0].release_reason)

    def test_pretty_print__single_lib__requires_release(self):
        a1 = self._create_library_artifact_node("g1", "a1", "1.0.0", "mylib",
                                                requires_release=True,
                                                release_reason=rr.ReleaseReason.FIRST)

        lib_nodes = libaggregator.get_libraries_to_release([a1,])
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
                                                release_reason=rr.ReleaseReason.FIRST)

        lib_nodes = libaggregator.get_libraries_to_release([a1,])
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
        lib_nodes = libaggregator.get_libraries_to_release([l1a1, l1a2])

        self.assertEqual(1, len(lib_nodes))
        self.assertEqual(1, len(lib_nodes[0].children))
        lib = lib_nodes[0]
        self.assertEqual("1.0.0-SNAPSHOT", lib.version)
        self.assertEqual(lib.library_path, "mylib")
        self.assertTrue(lib.requires_release)
        self.assertEqual(rr.ReleaseReason.ARTIFACT, lib.release_reason)

        lib = lib.children[0]
        self.assertEqual("2.0.0-SNAPSHOT", lib.version)
        self.assertEqual(lib.library_path, "mylib2")
        self.assertTrue(lib.requires_release)
        self.assertEqual(rr.ReleaseReason.ARTIFACT, lib.release_reason)

    def test_release_reason_precedence__always(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.TRANSITIVE))
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ALWAYS, rr.ReleaseReason.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__first(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.TRANSITIVE))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.FIRST, rr.ReleaseReason.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__artifact(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ReleaseReason.ARTIFACT, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.ARTIFACT, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.ARTIFACT, libaggregator._get_lib_release_reason(rr.ReleaseReason.ARTIFACT, rr.ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__pom(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ReleaseReason.ARTIFACT, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.POM, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.POM, libaggregator._get_lib_release_reason(rr.ReleaseReason.POM, rr.ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__transitive(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ReleaseReason.ARTIFACT, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.POM, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.TRANSITIVE, libaggregator._get_lib_release_reason(rr.ReleaseReason.TRANSITIVE, rr.ReleaseReason.TRANSITIVE))

    def test_release_reason_precedence__uncommitted(self):
        self.assertEqual(rr.ReleaseReason.ALWAYS, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.ALWAYS))
        self.assertEqual(rr.ReleaseReason.FIRST, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.FIRST))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.ARTIFACT))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.POM))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.TRANSITIVE))
        self.assertEqual(rr.ReleaseReason.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ReleaseReason.UNCOMMITTED_CHANGES, rr.ReleaseReason.UNCOMMITTED_CHANGES))

    def _create_library_artifact_node(self, group_id, artifact_id, version,
                                      library_path, requires_release,
                                      release_reason=None):
        dev_version = version + "-SNAPSHOT"
        released_version = version
        if requires_release and release_reason is None:
            release_reason = rr.ReleaseReason.ARTIFACT
        artifact_def =\
            buildpom.MavenArtifactDef(group_id, artifact_id, dev_version,
                                      released_version=released_version,
                                      library_path=library_path,
                                      requires_release=requires_release,
                                      bazel_target="t1")
        artifact_def.release_reason = release_reason
        return crawler.Node(parent=None, artifact_def=artifact_def,
                            label=label.Label(library_path))


if __name__ == '__main__':
    unittest.main()

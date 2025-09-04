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
        self.assertEqual(rr.ARTIFACT, lib_nodes[0].release_reason)

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
                                                release_reason=rr.FIRST)

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
                                                release_reason=rr.FIRST)

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
        self.assertEqual(rr.ARTIFACT, lib.release_reason)

        lib = lib.children[0]
        self.assertEqual("2.0.0-SNAPSHOT", lib.version)
        self.assertEqual(lib.library_path, "mylib2")
        self.assertTrue(lib.requires_release)
        self.assertEqual(rr.ARTIFACT, lib.release_reason)

    def test_release_reason_precedence__always(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.ALWAYS))
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.FIRST))
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.ARTIFACT))
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.MANIFEST))
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.TRANSITIVE))
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ALWAYS, rr.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__first(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.FIRST, rr.ALWAYS))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.FIRST, rr.FIRST))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.FIRST, rr.ARTIFACT))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.FIRST, rr.MANIFEST))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.FIRST, rr.TRANSITIVE))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.FIRST, rr.UNCOMMITTED_CHANGES))

    def test_release_reason_precedence__artifact(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.ALWAYS))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.FIRST))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ARTIFACT, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.ARTIFACT))
        self.assertEqual(rr.ARTIFACT, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.MANIFEST))
        self.assertEqual(rr.ARTIFACT, libaggregator._get_lib_release_reason(rr.ARTIFACT, rr.TRANSITIVE))

    def test_release_reason_precedence__pom(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.ALWAYS))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.FIRST))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ARTIFACT, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.ARTIFACT))
        self.assertEqual(rr.MANIFEST, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.MANIFEST))
        self.assertEqual(rr.MANIFEST, libaggregator._get_lib_release_reason(rr.MANIFEST, rr.TRANSITIVE))

    def test_release_reason_precedence__transitive(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.ALWAYS))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.FIRST))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.UNCOMMITTED_CHANGES))
        self.assertEqual(rr.ARTIFACT, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.ARTIFACT))
        self.assertEqual(rr.MANIFEST, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.MANIFEST))
        self.assertEqual(rr.TRANSITIVE, libaggregator._get_lib_release_reason(rr.TRANSITIVE, rr.TRANSITIVE))

    def test_release_reason_precedence__uncommitted(self):
        self.assertEqual(rr.ALWAYS, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.ALWAYS))
        self.assertEqual(rr.FIRST, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.FIRST))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.ARTIFACT))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.MANIFEST))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.TRANSITIVE))
        self.assertEqual(rr.UNCOMMITTED_CHANGES, libaggregator._get_lib_release_reason(rr.UNCOMMITTED_CHANGES, rr.UNCOMMITTED_CHANGES))

    def _create_library_artifact_node(self, group_id, artifact_id, version,
                                      library_path, requires_release,
                                      release_reason=None):
        dev_version = version + "-SNAPSHOT"
        released_version = version
        if requires_release and release_reason is None:
            release_reason = rr.ARTIFACT
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

"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import bazel
from crawl import dependency
import os
import unittest
import tempfile


class BazelTest(unittest.TestCase):

    def test_parse_maven_install(self):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT)

        result = bazel.parse_maven_install([("maven", path,)])
        self.assertEqual(7, len(result))
        dep, transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-classic", "maven")
        self.assertEqual("1.2.3", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(3, len(transitives))
        self.assertEqual(dependency.new_dep_from_maven_art_str("ch.qos.logback:logback-core:1.2.3", "maven"), transitives[0])
        self.assertEqual(dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven"), transitives[1])
        self.assertEqual(dependency.new_dep_from_maven_art_str("org.slf4j:slf4j-api:jar:1.7.30", "maven"), transitives[2])

        dep, transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-core", "maven")
        self.assertEqual("1.2.3", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(1, len(transitives))
        self.assertEqual(dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven"), transitives[0])

        dep, transitives = self._get_dep_and_transitives(
            result, "org.slf4j", "slf4j-api", "maven")
        self.assertEqual("1.7.30", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(0, len(transitives))

        dep, transitives = self._get_dep_and_transitives(
            result, "google.guava", "guava", "maven")
        self.assertEqual("1.0.0", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(0, len(transitives))

        dep, transitives = self._get_dep_and_transitives(
            result, "org.apache.kafka", "kafka-clients", "maven")
        self.assertEqual("3.4.0", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual("test", dep.classifier)
        self.assertEqual(2, len(transitives))
        self.assertEqual(dependency.new_dep_from_maven_art_str("ch.qos.logback:logback-core:1.2.3", "maven"), transitives[0])
        self.assertEqual(dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven"), transitives[1])

        dep, transitives = self._get_dep_and_transitives(
            result, "org.springframework.kafka", "spring-kafka-test", "maven")
        self.assertEqual("2.9.13", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(3, len(transitives))
        self.assertEqual(dependency.new_dep_from_maven_art_str("org.apache.kafka:kafka-clients:jar:test:3.4.0", "maven"), transitives[0])
        self.assertEqual(dependency.new_dep_from_maven_art_str("ch.qos.logback:logback-core:1.2.3", "maven"), transitives[1])
        self.assertEqual(dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven"), transitives[2])

    def test_parse_maven_install__dependency_identity(self):
        """
        Ensures that parsed deps are singletons.
        """
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT)

        result = bazel.parse_maven_install([("maven", path)])

        guava_dep, _ = self._get_dep_and_transitives(
            result, "google.guava", "guava", "maven")
        _, logback_transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-core", "maven")
        self.assertEqual(dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven"), logback_transitives[0])
        # the guava transitive is the same instance as the guava top level dep:
        self.assertIs(guava_dep, logback_transitives[0])

    def test_parse_maven_install__with_overrides(self):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT)
        guava = dependency.new_dep_from_maven_art_str("google.guava:guava:0.0.1", "maven")
        antlr = dependency.new_dep_from_maven_art_str("antlr:antlr:1.0.0", "maven")

        label_to_overridden_fq_label = {guava.unqualified_bazel_label_name: antlr.bazel_label_name}

        result = bazel.parse_maven_install([("maven", path)], label_to_overridden_fq_label)

        dep, transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-classic", "maven")
        self.assertEqual("1.2.3", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(3, len(transitives))
        self.assertEqual(dependency.new_dep_from_maven_art_str("ch.qos.logback:logback-core:1.2.3", "maven"), transitives[0])
        # this is antlr instead of guava because of the overrides
        self.assertEqual(transitives[1], antlr)
        self.assertEqual(dependency.new_dep_from_maven_art_str("org.slf4j:slf4j-api:jar:1.7.30", "maven"), transitives[2])
        dep, _  = self._get_dep_and_transitives(
            result, guava.group_id, guava.artifact_id, "maven")
        # the top level guava dep is still there
        self.assertEqual(guava, dep)

    def test_parse_maven_install__with_overrides__multiple_mvn_inst_rules(self):
        fd, path1 = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT_SIMPLE_1)
        fd, path2 = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT_SIMPLE_2)
        logback_core = dependency.new_dep_from_maven_art_str("ch.qos.logback:logback-core:1.0.0", "maven")
        zookeeper = dependency.new_dep_from_maven_art_str("org.apache:zookeeper:1.0.0", "maven")
        antlr = dependency.new_dep_from_maven_art_str("antlr:antlr:1.0.0", "maven")
        guava = dependency.new_dep_from_maven_art_str("google.guava:guava:1.0.0", "maven")

        label_to_overridden_fq_label = {
            logback_core.unqualified_bazel_label_name: zookeeper.bazel_label_name,
            guava.unqualified_bazel_label_name: antlr.bazel_label_name
        }

        result = bazel.parse_maven_install(
            [("maven", path1), ("nevam", path2)],
            label_to_overridden_fq_label)

        dep, transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-classic", "maven")
        self.assertEqual("1.0.0", dep.version)
        self.assertEqual("jar", dep.packaging)
        self.assertEqual(None, dep.classifier)
        self.assertEqual(2, len(transitives))
        self.assertEqual(zookeeper, transitives[0])
        self.assertEqual(antlr, transitives[1])


        maven_antlr, _ = self._get_dep_and_transitives(
            result, "antlr", "antlr", "maven")
        dep, transitives = self._get_dep_and_transitives(
            result, "ch.qos.logback", "logback-classic", "nevam")
        self.assertTrue(dep.bazel_label_name.startswith("@nevam"))
        self.assertEqual(1, len(transitives))
        self.assertTrue(antlr.bazel_label_name.startswith("@maven"))
        self.assertIs(maven_antlr, transitives[0])

    def test_conflict_resolution_is_honored(self):
        """
        Verifies that the pinned file's "conflict_resolution" attribute is
        handled.
        """
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(MVN_INSTALL_JSON_CONTENT_CONFLICT_RESOLUTION)

        result = bazel.parse_maven_install([("maven", path)])

        expected_guava = dependency.new_dep_from_maven_art_str("com.google.guava:guava:31.0.1-jre", "maven")
        self.assertEqual(2, len(result))
        _, transitives = self._get_dep_and_transitives(result, "ch.qos.logback", "logback-classic", "maven")
        self.assertEqual(1, len(transitives))
        transitive_guava = transitives[0]
        # we expect to get the dep from conflict_resolution map
        self.assertEqual(expected_guava, transitive_guava)
        self.assertEqual(expected_guava.version, transitive_guava.version)
        guava, _ = self._get_dep_and_transitives(result, "com.google.guava", "guava", "maven")
        # we expect to get the dep from conflict_resolution map
        self.assertEqual(expected_guava, guava)
        self.assertEqual(expected_guava.version, guava.version)

    def test_target_pattern_to_path(self):
        """
        Tests for bazel.target_pattern_to_path.
        """
        self.assertEqual("foo/blah", bazel.target_pattern_to_path("//foo/blah"))
        self.assertEqual("foo/blah", bazel.target_pattern_to_path("/foo/blah"))
        self.assertEqual("foo/blah", bazel.target_pattern_to_path("foo/blah:target_name"))
        self.assertEqual("foo/blah", bazel.target_pattern_to_path("foo/blah/..."))
        self.assertEqual("foo/blah", bazel.target_pattern_to_path("foo/blah"))

    def test_ensure_unique_deps(self):
        """
        Tests for bazel._ensure_unique_deps
        """
        self.assertEqual(["//a", "//b", "//c"],
                          bazel._ensure_unique_deps(["//a", "//b", "//c", "//a"]))

    def test_use_alt_lookup_coords(self):
        d1 = dependency.new_dep_from_maven_art_str("com.salesforce.servicelibs:pki-security-impl:jar:tests:1.0.0", "maven")
        top_level_deps = [d1]
        coord_wo_vers_to_dep = {d.maven_coordinates_name:d for d in top_level_deps}
        direct_dep_coords_wo_vers = ["com.salesforce.servicelibs:pki-security-impl:test-jar"]

        direct_deps = bazel._get_direct_deps(direct_dep_coords_wo_vers,
                                             coord_wo_vers_to_dep, "test_install.bzl", True, True)

        self.assertIn(d1, direct_deps)

    def _get_dep_and_transitives(self, result, group_id, artifact_id, rule_name):
        for t in result:
            d = t[0]
            # startswith is not correct when there are common prefixes, but
            # this is a test, so its ok
            if d.group_id == group_id and d.artifact_id == artifact_id and d.bazel_label_name.startswith("@" + rule_name):
                return t
        assert False, "didn't find %s:%s in result:\n%s" % (group_id, artifact_id, result)


MVN_INSTALL_JSON_CONTENT = """
{
    "artifacts": {
        "ch.qos.logback:logback-classic": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac",
                "sources": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.2.3"
        },
        "ch.qos.logback:logback-core": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.2.3"
        },
        "org.slf4j:slf4j-api": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.7.30"
        },
        "google.guava:guava": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "antlr:antlr": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "org.apache.kafka:kafka-clients": {
            "shasums": {
                "jar": "48f38dede69bf2ed3709e270afb6b72fac869651fc258997727dba350333ac64",
                "sources": "6778050b189bf2eab414e4c5004d97f49f9a7635b21fe23e73d5ba131202f829",
                "test": "217e7ce92a3f0e3ebc594554662c29a238395b8428f32630904af608f5d18740"
            },
            "version": "3.4.0"
        },
        "org.springframework.kafka:spring-kafka-test": {
            "shasums": {
                "jar": "dbccbb02d733338525112512fe64f52b2c08f06695579aa090e3630ebe973223",
                "sources": "3041f5c7744c9e21b7f8ffd3688a8433388f2fb0e135ab2a75b99fc8cea1ed9c"
            },
            "version": "2.9.13"
        }
    },
    "dependencies": {
        "ch.qos.logback:logback-classic": [
            "ch.qos.logback:logback-core",
            "org.slf4j:slf4j-api"
        ],
        "ch.qos.logback:logback-core": [
            "google.guava:guava"
        ],
        "org.apache.kafka:kafka-clients:jar:test": [
            "ch.qos.logback:logback-core",
            "org.kie.modules:org-apache-commons-lang3:pom"
        ],
        "org.springframework.kafka:spring-kafka-test": [
            "org.apache.kafka:kafka-clients:jar:test"
        ]
    },
    "repositories": {
        "https://maven.google.com/": [
            "antlr:antlr",
            "org.springframework.kafka:spring-kafka-test",
            "ch.qos.logback:logback-classic",
            "ch.qos.logback:logback-classic:jar:sources",
            "ch.qos.logback:logback-core",
            "org.slf4j:slf4j-api",
            "google.guava:guava",
            "org.apache.kafka:kafka-clients:jar:test"
        ]
    },
    "version": "2"
}
"""


MVN_INSTALL_JSON_CONTENT_SIMPLE_1 = """
{
    "artifacts": {
        "ch.qos.logback:logback-classic": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac",
                "sources": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "ch.qos.logback:logback-core": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "google.guava:guava": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "antlr:antlr": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "org.apache:zookeeper": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        }
    },
    "dependencies": {
        "ch.qos.logback:logback-classic": [
            "ch.qos.logback:logback-core"
        ],
        "ch.qos.logback:logback-core": [
            "google.guava:guava"
        ],
        "org.apache:zookeeper": [
            "google.guava:guava"
        ]
    },
    "repositories": {
        "https://maven.google.com/": [
            "antlr:antlr",
            "ch.qos.logback:logback-classic",
            "ch.qos.logback:logback-core",
            "google.guava:guava",
            "org.apache:zookeeper"
        ]
    },
    "version": "2"
}
"""


MVN_INSTALL_JSON_CONTENT_SIMPLE_2 = """
{
    "artifacts": {
        "ch.qos.logback:logback-classic": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac",
                "sources": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        },
        "google.guava:guava": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.0.0"
        }
    },
    "dependencies": {
        "ch.qos.logback:logback-classic": [
            "google.guava:guava"
        ]
    },
    "repositories": {
        "https://maven.google.com/": [
            "ch.qos.logback:logback-classic",
            "google.guava:guava"
        ]
    },
    "version": "2"
}
"""


MVN_INSTALL_JSON_CONTENT_CONFLICT_RESOLUTION = """
{
    "conflict_resolution": {
        "com.google.guava:guava:31.0.1-jre": "com.google.guava:guava:31.0.1-jre-SNAPSHOT"
    },
    "artifacts": {
        "ch.qos.logback:logback-classic": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "1.2.3"
        },
        "com.google.guava:guava": {
            "shasums": {
                "jar": "ef95ae468097f378880be69a8c6756f8d15180e0f07547fb0a99617ff421b2ac"
            },
            "version": "31.0.1-jre-SNAPSHOT"
        }
    },
    "dependencies": {
        "ch.qos.logback:logback-classic": [
            "com.google.guava:guava"
        ]
    },
    "repositories": {
        "https://maven.google.com/": [
            "ch.qos.logback:logback-classic",
            "com.google.guava:guava"
        ]
    },
    "version": "2"
}
"""


if __name__ == '__main__':
    unittest.main()

import unittest
from generate.impl.js.pnpmlockparser import PnpmLockParser


# lockfileVersion < 9: "dependencies:"/"devDependencies:" are flat,
# top-level keys.
FLAT_CONTENT = """
lockfileVersion: '6.0'

settings:
  autoInstallPeers: true
  excludeLinksFromLockfile: false

dependencies:
  figlet:
    specifier: ^1.11.0
    version: 1.11.0
  '@openfeature/flagd-provider':
    specifier: 0.18.0
    version: 0.18.0(@grpc/grpc-js@1.14.6)(@openfeature/core@1.12.0)(@openfeature/server-sdk@1.22.0)
  msw-legacy:
    specifier: npm:msw@0.49.3
    version: /msw@0.49.3(@types/node@18.11.9)(encoding@0.1.13)(typescript@5.4.5)

devDependencies:
  '@types/figlet':
    specifier: ^1.7.0
    version: 1.7.0
  typescript:
    specifier: 5.6.2
    version: 5.6.2

packages:

  '@types/figlet@1.7.0':
    resolution: {integrity: sha512-KwrT7p/8Eo3Op/HBSIwGXOsTZKYiM9NpWRBJ5sVjWP/SmlS+oxxRvJht/FNAtliJvja44N3ul1yATgohnVBV0Q==}

  figlet@1.11.0:
    resolution: {integrity: sha512-EEx3OS/l2bFqcUNN2NM9FPJp8vAMrgbCxsbl2hbcJNNxOEwVe3mEzrhan7TbJQViZa8mMqhihlbCaqD+LyYKTQ==}

  typescript@5.6.2:
    resolution: {integrity: sha512-NW8ByodCSNCwZeghjN3o+JX5OFH0Ojg6sadjEKY4huZ52TqbJTJnDo5+Tw98lSy63NZvi4n+ez5m2u5d4PkZyw==}
"""


# lockfileVersion >= 9: "dependencies:"/"devDependencies:" live under
# "importers:" -> ".:", even for a single, non-workspace project.
IMPORTERS_CONTENT = """
lockfileVersion: '9.0'

settings:
  autoInstallPeers: true
  excludeLinksFromLockfile: false

importers:

  .:
    dependencies:
      figlet:
        specifier: ^1.11.0
        version: 1.11.0
    devDependencies:
      '@types/figlet':
        specifier: ^1.7.0
        version: 1.7.0
      typescript:
        specifier: 5.6.2
        version: 5.6.2

packages:

  '@types/figlet@1.7.0':
    resolution: {integrity: sha512-KwrT7p/8Eo3Op/HBSIwGXOsTZKYiM9NpWRBJ5sVjWP/SmlS+oxxRvJht/FNAtliJvja44N3ul1yATgohnVBV0Q==}

  commander@14.0.3:
    resolution: {integrity: sha512-H+y0Jo/T1RZ9qPP4Eh1pkcQcLRglraJaSLoyOtHxu6AapkjWVCy2Sit1QQ4x3Dng8qDlSsZEet7g5Pq06MvTgw==}
    engines: {node: '>=20'}

  figlet@1.11.0:
    resolution: {integrity: sha512-EEx3OS/l2bFqcUNN2NM9FPJp8vAMrgbCxsbl2hbcJNNxOEwVe3mEzrhan7TbJQViZa8mMqhihlbCaqD+LyYKTQ==}
    engines: {node: '>= 17.0.0'}
    hasBin: true

  typescript@5.6.2:
    resolution: {integrity: sha512-NW8ByodCSNCwZeghjN3o+JX5OFH0Ojg6sadjEKY4huZ52TqbJTJnDo5+Tw98lSy63NZvi4n+ez5m2u5d4PkZyw==}
    engines: {node: '>=14.17'}
    hasBin: true

snapshots:

  '@types/figlet@1.7.0': {}

  commander@14.0.3: {}

  figlet@1.11.0:
    dependencies:
      commander: 14.0.3

  typescript@5.6.2: {}
"""


class PnpmLockParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = PnpmLockParser()

    def test_parse_flat_lockfile(self):
        """lockfileVersion < 9: "dependencies:"/"devDependencies:" are
        top-level keys."""
        non_dev_deps, dev_deps = self.parser.parse_pnpm_lock_file(FLAT_CONTENT)

        self.assertEqual(3, len(non_dev_deps))
        self.assertEqual(("figlet", "1.11.0"), non_dev_deps[0])
        self.assertEqual(("@openfeature/flagd-provider", "0.18.0"), non_dev_deps[1])
        self.assertEqual(("msw-legacy", "0.49.3"), non_dev_deps[2])

        self.assertEqual(2, len(dev_deps))
        self.assertEqual(("@types/figlet", "1.7.0"), dev_deps[0])
        self.assertEqual(("typescript", "5.6.2"), dev_deps[1])

    def test_parse_importers_nested_lockfile(self):
        """lockfileVersion >= 9: "dependencies:"/"devDependencies:" live
        under "importers:" -> ".:"."""
        non_dev_deps, dev_deps = self.parser.parse_pnpm_lock_file(IMPORTERS_CONTENT)

        self.assertEqual(1, len(non_dev_deps))
        self.assertEqual(("figlet", "1.11.0"), non_dev_deps[0])

        self.assertEqual(2, len(dev_deps))
        self.assertEqual(("@types/figlet", "1.7.0"), dev_deps[0])
        self.assertEqual(("typescript", "5.6.2"), dev_deps[1])

    def test_ignores_transitive_only_versions_in_packages_section(self):
        """A package can appear in "packages:" at a different version than
        the one the root project actually depends on (e.g. pulled in
        transitively, at a newer or older version, by some other
        dependency). Only the root's own resolved version - from
        "dependencies:"/"devDependencies:" - must be returned."""
        content = """
dependencies:
  '@types/node':
    specifier: ^18.11.9
    version: 18.11.9

packages:

  '@types/node@18.11.9':
    resolution: {integrity: sha512-aaa==}

  '@types/node@24.19.2':
    resolution: {integrity: sha512-bbb==}
    dependencies:
      undici-types: 7.24.6
"""
        non_dev_deps, dev_deps = self.parser.parse_pnpm_lock_file(content)

        self.assertEqual([("@types/node", "18.11.9")], non_dev_deps)
        self.assertEqual([], dev_deps)


if __name__ == '__main__':
    unittest.main()

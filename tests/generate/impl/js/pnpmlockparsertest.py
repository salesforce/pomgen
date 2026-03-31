import unittest
from generate.impl.js.pnpmlockparser import PnpmLockParser


CONTENT = """
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

    def test_parse_pnpm_lock_file(self):
        non_dev_deps, dev_deps = self.parser.parse_pnpm_lock_file(CONTENT)

        # All 4 packages are non-dev since none have dev: true marker
        self.assertEqual(4, len(non_dev_deps))
        self.assertEqual(0, len(dev_deps))

        types_figlet = non_dev_deps[0]
        self.assertEqual("@types/figlet", types_figlet[0])
        self.assertEqual("1.7.0", types_figlet[1])

        commander = non_dev_deps[1]
        self.assertEqual("commander", commander[0])
        self.assertEqual("14.0.3", commander[1])

        figlet = non_dev_deps[2]
        self.assertEqual("figlet", figlet[0])
        self.assertEqual("1.11.0", figlet[1])

        typescript = non_dev_deps[3]
        self.assertEqual("typescript", typescript[0])
        self.assertEqual("5.6.2", typescript[1])

    def test_parse_with_nested_properties(self):
        """Test that nested properties like 'dependencies:', 'engines:', etc. are ignored and dev dependencies are separated"""
        content = """
packages:

  /@types/figlet@1.7.0:
    resolution: {integrity: sha512-KwrT7p/8Eo3Op/HBSIwGXOsTZKYiM9NpWRBJ5sVjWP/SmlS+oxxRvJht/FNAtliJvja44N3ul1yATgohnVBV0Q==}
    dev: true

  /commander@14.0.3:
    resolution: {integrity: sha512-H+y0Jo/T1RZ9qPP4Eh1pkcQcLRglraJaSLoyOtHxu6AapkjWVCy2Sit1QQ4x3Dng8qDlSsZEet7g5Pq06MvTgw==}
    engines: {node: '>=20'}
    dev: false

  /figlet@1.11.0:
    resolution: {integrity: sha512-EEx3OS/l2bFqcUNN2NM9FPJp8vAMrgbCxsbl2hbcJNNxOEwVe3mEzrhan7TbJQViZa8mMqhihlbCaqD+LyYKTQ==}
    engines: {node: '>= 17.0.0'}
    hasBin: true
    dependencies:
      commander: 14.0.3
    dev: false

  /typescript@5.6.2:
    resolution: {integrity: sha512-NW8ByodCSNCwZeghjN3o+JX5OFH0Ojg6sadjEKY4huZ52TqbJTJnDo5+Tw98lSy63NZvi4n+ez5m2u5d4PkZyw==}
    engines: {node: '>=14.17'}
    hasBin: true
    dev: true
"""
        non_dev_deps, dev_deps = self.parser.parse_pnpm_lock_file(content)

        # Non-dev dependencies (dev: false or no dev marker)
        self.assertEqual(2, len(non_dev_deps))

        commander = non_dev_deps[0]
        self.assertEqual("commander", commander[0])
        self.assertEqual("14.0.3", commander[1])

        figlet = non_dev_deps[1]
        self.assertEqual("figlet", figlet[0])
        self.assertEqual("1.11.0", figlet[1])

        # Dev dependencies (dev: true)
        self.assertEqual(2, len(dev_deps))

        types_figlet = dev_deps[0]
        self.assertEqual("@types/figlet", types_figlet[0])
        self.assertEqual("1.7.0", types_figlet[1])

        typescript = dev_deps[1]
        self.assertEqual("typescript", typescript[0])
        self.assertEqual("5.6.2", typescript[1])


if __name__ == '__main__':
    unittest.main()

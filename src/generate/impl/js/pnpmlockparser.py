class PnpmLockParser:
    """
    pnpm-lock.yaml file parser.
    """
    def parse_pnpm_lock_file(self, content):
        """
        Parses the pnpm-lock.yaml file content into two lists of tuples
        consisting of (name[str], version[str]).

        Args:
            content: Content of a pnpm-lock.yaml file

        Returns:
            (runtime_dependencies, dev_dependencies), where each is a list of tuples.
        """
        return self._parse_dependencies(content)

    def _parse_dependencies(self, content):
        non_dev_dependencies = []
        dev_dependencies = []
        in_packages_section = False
        lines = content.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if len(stripped) == 0:
                i += 1
                continue

            if stripped == "packages:":
                in_packages_section = True
                i += 1
                continue

            if in_packages_section and line and not line.startswith('  '):
                in_packages_section = False

            if not in_packages_section:
                i += 1
                continue

            if not stripped.endswith(":"):
                i += 1
                continue

            package_key = stripped[:-1] # remove trailing ':'

            if package_key in _NESTED_ATTRIBUTES:
                i += 1
                continue

            if (package_key.startswith("'") and package_key.endswith("'")) or \
               (package_key.startswith('"') and package_key.endswith('"')):
                package_key = package_key[1:-1]

            # Skip if no @ sign (not a valid package entry)
            if '@' not in package_key:
                i += 1
                continue

            at_index = package_key.rindex("@")
            name = package_key[:at_index]
            version = package_key[at_index + 1:]

            # Strip leading '/' from name (pnpm lock file format)
            if name.startswith('/'):
                name = name[1:]

            # Check if this is a dev-only dependency
            is_dev_only = False
            # Look ahead at the nested properties for this package
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()

                # Stop if we hit another package or exit packages section
                if next_line and not next_line.startswith('  '):
                    break
                if next_stripped.endswith(':') and next_stripped[:-1] not in _NESTED_ATTRIBUTES:
                    break

                # Check for dev: true
                if next_stripped == "dev: true":
                    is_dev_only = True
                    break

                j += 1

            if is_dev_only:
                dev_dependencies.append((name, version))
            else:
                non_dev_dependencies.append((name, version))

            i += 1

        return (non_dev_dependencies, dev_dependencies)


_NESTED_ATTRIBUTES = (
    "resolution", "engines", "dev", "hasBin", "dependencies",
    "devDependencies", "optionalDependencies", "peerDependencies",
    "os", "cpu", "deprecated", "bundledDependencies"
)


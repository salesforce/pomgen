class PnpmLockParser:
    """
    pnpm-lock.yaml file parser.

    Reads the root project's "dependencies:"/"devDependencies:" sections -

    Supports both pnpm lockfile layouts:
      - flat (lockfileVersion < 9): "dependencies:"/"devDependencies:" are
        top-level keys.
      - importers-nested (lockfileVersion >= 9): "dependencies:"/
        "devDependencies:" live under "importers:" -> ".:", even for a
        single, non-workspace project.
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
        lines = content.splitlines()
        start, base_indent, end = self._locate_root_section(lines)
        non_dev_dependencies = self._parse_section(
            lines, start, end, "dependencies", base_indent)
        dev_dependencies = self._parse_section(
            lines, start, end, "devDependencies", base_indent)
        return non_dev_dependencies, dev_dependencies

    def _locate_root_section(self, lines):
        for i, line in enumerate(lines):
            if line == "importers:":
                start = self._find_importer_block_start(lines, i)
                end = self._find_block_end(lines, start, base_indent=4)
                return start, 4, end
        return 0, 0, len(lines)

    def _find_importer_block_start(self, lines, importers_index):
        i = importers_index + 1
        while i < len(lines):
            line = lines[i]
            if line.strip() == "":
                i += 1
                continue
            if line == "  .:":
                return i + 1
            i += 1
        raise AssertionError(
            "pnpm-lock.yaml has an \"importers:\" section but no \".:\" "
            "entry under it - multi-project (workspace) lockfiles are not "
            "supported")

    def _find_block_end(self, lines, start, base_indent):
        i = start
        while i < len(lines):
            line = lines[i]
            if line.strip() != "" and self._indent_of(line) < base_indent:
                return i
            i += 1
        return len(lines)

    def _parse_section(self, lines, start, end, section_name, base_indent):
        header_line = (" " * base_indent) + section_name + ":"
        header_index = None
        for i in range(start, end):
            if lines[i] == header_line:
                header_index = i
                break
        if header_index is None:
            return []

        entry_indent = base_indent + 2
        attr_indent = base_indent + 4
        dependencies = []
        current_name = None
        i = header_index + 1
        while i < end:
            line = lines[i]
            if line.strip() == "":
                i += 1
                continue
            indent = self._indent_of(line)
            if indent <= base_indent:
                break
            if indent == entry_indent:
                stripped = line.strip()
                assert stripped.endswith(":"), \
                    "Expected a package entry, got [%s]" % line
                current_name = self._strip_quotes(stripped[:-1])
            elif indent == attr_indent:
                stripped = line.strip()
                if stripped.startswith("version:"):
                    assert current_name is not None
                    version = self._extract_version(stripped[len("version:"):])
                    dependencies.append((current_name, version))
            i += 1
        return dependencies

    @classmethod
    def _indent_of(clazz, line):
        return len(line) - len(line.lstrip(" "))

    @classmethod
    def _strip_quotes(clazz, value):
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return value[1:-1]
        return value

    @classmethod
    def _extract_version(clazz, raw_value):
        # Handles plain versions ("1.0.0"), versions with a trailing
        # parenthesized peer-dependency suffix
        # ("0.18.0(@grpc/grpc-js@1.14.6)"), and npm-aliased versions
        # ("/msw@0.49.3(...)" for a dependency declared as
        # "npm:msw@0.49.3").
        value = clazz._strip_quotes(raw_value.strip())
        if value.startswith("/"):
            value = value[1:]
        paren_index = value.find("(")
        base = value if paren_index == -1 else value[:paren_index]
        if "@" in base:
            at_index = base.rindex("@")
            return base[at_index + 1:]
        return base

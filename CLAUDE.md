# Etiquette

- Keep answers short
- Ask if something is unclear, do not assume anything
- Confirm plan before making code changes


# Verification of code changes

For verification of all code changes made, always run:

`bazel test //...` from the root directory (this directory)
The command above should complete without errors.
Note that it isn't necessary to run bazel test on individual targets targets since the codebase is small - for simplicity just always use `bazel test //...`.

`bazel run //:gen -- --package examples --destdir tests/examples_goldfiles`
The command above should complete without errors
There should be no diffs un the tests/examples_goldfiles directory

`ruff check src tests misc`
The command above should complete without errors


# Formatting

After making code changes, make sure there are no leading or trailing spaces shown in `git diff` output.

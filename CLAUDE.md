# Etiquette

- Keep answers short
- Ask if something is unclear, do not assume anything
- Confirm plan before making code changes


# Making code changes

## Verification

### Unit tests

For verification of all code changes made, always run:

`bazel test //...` from the root directory (this directory)
The command above should complete without errors.
Note that it isn't necessary to run bazel test on individual targets targets since the codebase is small - for simplicity just always use `bazel test //...`.

### Goldfile tests

`./tests/examples_goldfiles/run_goldfiles_test.sh`
The command above should complete without errors.
After running this command, there should be no diffs under the tests/examples_goldfiles/examples directory.

### Formatting and Linting (automated)

`ruff check src tests misc`
The command above should complete without errors.


### Formatting (manual)

After making code changes, make sure there are no leading or trailing spaces shown in `git diff` output.



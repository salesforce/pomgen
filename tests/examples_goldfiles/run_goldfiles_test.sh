set -e


# remove all files so we notice when expected files are not written
rm -rf tests/examples_goldfiles/examples

# generate all manifest files for all example artifacts
bazel run //:gen -- --package examples --destdir tests/examples_goldfiles

# for the java/juicer example library, write the libraries hint file
# the hint file is only written when a specific library is specified
# also use the "description" option
bazel run //:gen -- \
  --package examples/java/hello-world/juicer \
  --destdir tests/examples_goldfiles \
  --write_libraries_hint_file \
  --manifest_description "this is a call!"

# generate the manifet goldfiles for all example artifacts
bazel run //:gen -- --package examples --destdir tests/examples_goldfiles --manifest_goldfile

# query output
bazel run //:query -- --list_external_dependencies > tests/examples_goldfiles/external_dependencies.json

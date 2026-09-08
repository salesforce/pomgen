set -e


# remove all files so we notice when expected files are not written
rm -rf tests/examples_goldfiles/examples

# generate all manifest files for all example artifacts
bazel run //:gen -- --package examples --destdir tests/examples_goldfiles

# for the java/juicer example library, write the libraries hint file
# the hint file is only written when a specific library is specified
# also test setting manifest_metadata, through the package/maven wrapper
# script, which turns POM_METADATA_* env vars into --manifest_metadata
POM_METADATA_DESCRIPTION="this is a call!" bazel run @poppy//package/maven -- \
  -a pomgen \
  -l examples/java/hello-world/juicer

# package/maven always writes generated files into bazel-bin, so copy the
# ones we just generated into the source tree, to be diffed against the
# checked-in goldfiles below
for f in \
  examples/java/hello-world/juicer/pom.xml \
  examples/java/hello-world/juicer/libraries.txt \
  examples/java/hello-world/juicer/bazel_labels.txt \
  examples/java/hello-world/wintervegetables/pom.xml \
  examples/java/hello-world/healthyfoods/fruit-api/pom.xml \
  examples/java/hello-world/healthyfoods/vegetable-api/pom.xml \
  examples/java/hello-world/healthyfoods/parentpom/pom.xml \
; do
  cp -f "bazel-bin/$f" "tests/examples_goldfiles/$f"
done

# generate the manifest goldfiles for all example artifacts
bazel run //:gen -- --package examples --destdir tests/examples_goldfiles --manifest_goldfile

# query output
bazel run //:query -- --list_external_dependencies > tests/examples_goldfiles/external_dependencies.json

# list libraries
bazel run //:query -- --library_release_plan_json --package examples > tests/examples_goldfiles/libraries_release_plan.json

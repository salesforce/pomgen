#!/bin/bash

set -e

# update release metadata to simulate a release
# see ../../docs/ci.md
# run the script from the root of the repository

bazel run @poppy//:update -- --package examples/java/hello-world --new_released_version 0.0.1 --update_released_artifact_hash_to_current

bazel run @poppy//:gen -- --package examples/java/hello-world --destdir `pwd` --manifest_goldfile --force

echo "Next, commit the changes - this script won't do that for you"

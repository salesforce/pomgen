#!/bin/bash

# update release metadata to simulate a release
# see ../../docs/ci.md
# run the script from the root of the repository

bazel run @pomgen//:update -- --package examples/hello-world --new_released_version 0.0.1 --update_released_artifact_hash_to_current

bazel run @pomgen//:pomgen -- --package examples/hello-world --destdir `pwd` --recursive --pom_goldfile --force

echo "Next, commit the changes - this script won't do that for you"

# Copyright (c) 2025, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

# Shared logic used by the per-language packaging scripts (package/maven,
# package/npm, package/py) to run the "build" action, which runs
# "bazel build" on the Bazel labels that the "gen" action discovered while
# crawling a library and its upstream references. This logic is
# language-agnostic: it only deals with poppy's own hint files (written by
# "bazel run @poppy//:gen -- --write_libraries_hint_file") and Bazel itself,
# nothing specific to Maven, npm or Python packaging.

# 1st arg: path to root of repo
# 2nd arg: library path, must start with a '/'
_libraries_hint_file_path() {
    local repo_root_path=$1
    local library=$2
    echo "$repo_root_path/bazel-bin$library/libraries.txt"
}

# 1st arg: path to root of repo
# 2nd arg: library path, must start with a '/'
_bazel_labels_file_path() {
    local repo_root_path=$1
    local library=$2
    echo "$repo_root_path/bazel-bin$library/bazel_labels.txt"
}

# echoes "true" if the libraries hint file (written by the "gen" action) is
# available and should be used, "false" otherwise
# 1st arg: path to root of repo
# 2nd arg: whether upstream references should be followed (true/false)
# 3rd arg: library path, must start with a '/'
_use_libraries_hint_file() {
    local repo_root_path=$1
    local follow_libraries=$2
    local library_path=$3

    if [ "$follow_libraries" = false ]; then
        echo "false"
    else
        if [ -z "$library_path" ]; then
            echo "false"
        else
            local path="$(_libraries_hint_file_path $repo_root_path $library_path)"
            if [ -f "$path" ]; then
                echo "true"
            else
                echo "false"
            fi
        fi
    fi
}

# Converts BZL_ACTION_ENV_* environment variables to --action_env arguments
# Example: BZL_ACTION_ENV_JAVA_HOME=/usr/lib -> --action_env JAVA_HOME=/usr/lib
_build_action_env_args() {
    local action_env_args=""
    local prefix="BZL_ACTION_ENV_"

    while IFS='=' read -r name value; do
        if [[ "$name" == ${prefix}* ]]; then
            local key="${name#$prefix}"
            action_env_args="${action_env_args} --action_env ${key}=${value}"
        fi
    done < <(env)

    echo "$action_env_args"
}

# Runs "bazel build" on the Bazel labels file written by the "gen" action for
# the given library. Does nothing if that file does not exist.
# 1st arg: path to root of repo
# 2nd arg: library path, must start with a '/'
# 3rd arg (optional): "true" to build every target in each label's package
#   (by appending "/..." to each label), instead of only the exact label.
#   This is useful when the exact label used for dependency discovery (for
#   example a ts_project target) is not the same target that needs to be
#   built to produce the final artifact (for example an npm_package "pkg"
#   target in the same package).
_run_bazel_build_action() {
    local repo_root_path=$1
    local root_library_path=$2
    local build_all_targets_in_package=${3:-false}

    local bazel_labels_file_path="$(_bazel_labels_file_path $repo_root_path $root_library_path)"
    if [ -f "$bazel_labels_file_path" ]; then
        echo ""
        echo "[INFO] Building bazel labels from: $bazel_labels_file_path"
        cat "$bazel_labels_file_path"
        echo ""
        local action_env_args="$(_build_action_env_args)"
        if [ "$build_all_targets_in_package" = "true" ]; then
            local targets=""
            while IFS= read -r label || [ -n "$label" ]; do
                if [ -z "$label" ]; then
                    continue
                fi
                # strip any ":target" suffix so we always build everything
                # in the package, even if a target_name was set explicitly
                local package_label="${label%%:*}"
                targets="${targets} ${package_label}/..."
            done < "$bazel_labels_file_path"
            local cmd="bazel build${action_env_args}${targets}"
            echo "[INFO] Running $cmd"
            eval $cmd
        else
            local cmd="bazel build${action_env_args} --target_pattern_file=\"${bazel_labels_file_path}\""
            echo "[INFO] Running $cmd"
            eval $cmd
        fi
    fi
}

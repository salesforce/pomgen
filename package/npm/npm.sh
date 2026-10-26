#!/bin/bash

# Copyright (c) 2025, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

set -e

print_usage() {
cat << EOF

Usage: bazel run @poppy//package/npm -a action(s) -l path/to/library/root/dir

  Required arguments:

  -a (actions)
    Specifies which action(s) to run, see below for detaols on the actions.
    Make sure you run 'gen' before trying other actions.
    The actions to run may be comma-separated if there is more than one,
    for example: -a gen,install,build

  -l (library path)
    Specify the path to a library.

  -i (ignore references)
    By default, the library specified using -l is used as a starting point and
    upstream libraries are processed as well. This behavior can be disabled
    using -i

  -d (debug)
    Enables debug logging

  -f (force)
    Run even if no changes to artifacts have been made

  -h (help)
    This message


  Mandatory action:
    gen: generates package.json files for the given library and upstream
         libraries.  IMPORTANT: this action is required to run at least once
         before any of the other actions.

    
  Other actions:
    install: assembles the npm package for the given library and its upstreams,
             copying each into its own directory under $GLOBAL_DIST_DIR, along
             with a root package.json that references them as npm workspaces.
             The environment variable GLOBAL_DIST_DIR must be set when running
             this action.

    build: builds all libraries being processed (bazel build path/to/lib/...).
           install expects all artifacts that will be packaged to exist -
           in case they do not, this action can be helpful.

EOF
}


_write_root_package_json() {
    local package_dest_root_dir=$1
    shift
    local project_names=("$@")

    local workspaces_list=""
    local name
    for name in "${project_names[@]}"; do
        if [ -n "$workspaces_list" ]; then
            workspaces_list="${workspaces_list},"$'\n'
        fi
        workspaces_list="${workspaces_list}        \"${name}\""
    done

    cat > $package_dest_root_dir/package.json <<EOF
{
    "name": "npm-packages",
    "version": "1.0.0",
    "private": true,
    "workspaces": [
${workspaces_list}
    ]
}
EOF
}

_for_each_pyproject() {
    local action=$1
    local repo_root=$2
    local project_root_dir=$3
    local project_filter_path=$4
    local package_base_filename=$5

    if ! [[ "$action" =~ ^(clean|install)$ ]]; then
        echo "ERROR: Unknown action $action" && exit 1
    fi

    if [ ! -d $project_root_dir ]; then
        echo "ERROR: project_root_dir does not exist: $project_root_dir"
        exit 1
    fi

    if [ "$action" == "install" ] && [ -z "$GLOBAL_DIST_DIR" ]; then
        echo "ERROR: the environment variable GLOBAL_DIST_DIR must be set to run the install action"
        exit 1
    fi

    local package_dest_root_dir=$GLOBAL_DIST_DIR
    rm -rf $package_dest_root_dir

    local project_names=()

    while read package_json_path; do
        # package_json_path: the location of the generated manifest in bazel-bin
        echo "INFO: Processing: $package_json_path"

        if [ "$action" == "clean" ]; then
            rm $package_json_path
        elif [ "$action" == "install" ]; then
            local root_project_path=$(dirname $package_json_path)
            local project_name=$(basename $root_project_path)
            local package_dest_dir=$package_dest_root_dir/$project_name
            mkdir -p $package_dest_dir
            local pkg_path=$root_project_path/pkg
            cp -r ${pkg_path}/* $package_dest_dir/
            chmod -R +w $package_dest_dir
            cp $package_json_path $package_dest_dir/package.json
            project_names+=("$project_name")
        fi
    done < <(find -L $project_root_dir$project_filter_path -name "${package_base_filename}.json")

    if [ "$action" == "install" ] && [ ${#project_names[@]} -gt 0 ]; then
        _write_root_package_json $package_dest_root_dir "${project_names[@]}"
    fi
}

_run_actions() {
    local actions=$1
    local package_base_filename=$2
    for action in $(echo $actions | tr "," "\n")
    do
        if ! [[ "$action" =~ ^(clean|gen|install|build)$ ]]; then
            echo "[ERROR] action [$action] must be one of [clean|gen|install|build]" && exit 1
        fi

        repo_root=$PWD
        bazel_bin_dir=$repo_root/bazel-bin
        if [ ! -d $bazel_bin_dir ]; then
            echo "ERROR: bazel-bin doesn't exist, run `bazel build` on something."
           exit 1
        fi

        echo ""
        echo "Running action [$action]"
        echo ""

        if [ "$action" == "gen" ]; then
            local extra_args="--write_libraries_hint_file"
            if [ "$debug" = true ]; then
                extra_args="${extra_args} --verbose"
            fi
            if [ "$force_gen" = true ]; then
                extra_args="${extra_args} --force"
            fi
            if [ "$follow_references" = false ]; then
                extra_args="${extra_args} --ignore_references"
            fi
            echo "[DEBUG] Running poppy with extra args ${extra_args}"
            bazel run @poppy//:gen -- --package $library_path --destdir $bazel_bin_dir $extra_args
        elif [ "$action" == "build" ]; then
            if [ "$(_use_libraries_hint_file $repo_root $follow_references $library_path)" == "true" ]; then
                _run_bazel_build_action $repo_root $library_path true
            else
                echo "[ERROR] The 'build' action requires -l to point to a library"
                echo "        The 'gen' action must already have run for this library"
                echo "        Building is not supported with -i, you can just run"
                echo "        'bazel build' directly if you do not want to follow references"
                exit 1
            fi
        else
            _for_each_pyproject $action $repo_root $bazel_bin_dir $library_path $package_base_filename
        fi
    done
}


if [ "$#" -eq 0 ]; then
  print_usage && exit 1
fi

library_path=""
force_gen=false
follow_references=true
debug=false

while getopts "a:l:t:dhfi" option; do
  case $option in
    a ) actions=$OPTARG
    ;;
    l ) library_path=$OPTARG
    ;;
    d ) debug=true
    ;;
    f ) force_gen=true
    ;;
    i ) follow_references=false
    ;;
    h ) print_usage && exit 1
    ;;
  esac
done

if [ "$debug" = true ]; then
    echo "[DEBUG] Debug logging enabled"
fi

if [ -z "$actions" ] ; then
    echo "[ERROR] The action(s) to run must be specified using -a, for example:"
    echo "        $ bazel run @poppy//package/npm -- -a gen"
    echo "        bazel run @poppy//package/npm for usage information."
    exit 1
fi


if [ -z "$library_path" ] ; then
    echo "[INFO] No library specified, giving up"
    exit 1
elif [[ $library_path != /* ]]; then
    # library_path needs to start with a '/'
    library_path=/$library_path
fi


echo "[INFO] Running ${actions} for library: ${library_path}"

# load helper functions
_source_helper_file() {
    local package_dir=$1
    local helper_functions_file=$2

    local loaded=false
    local p="external/_main~_repo_rules~poppy/${package_dir}/${helper_functions_file}"
    if [ -f "${p}" ]; then
        # MODULE.bazel external repository path
        source "${p}"
        loaded=true
    fi
    if [ "$loaded" = false ]; then
        p="${package_dir}/${helper_functions_file}"
        if [ -f "${p}" ]; then
            # when running locally in this repository
            source "${p}"
            loaded=true
        fi
    fi
    if [ "$loaded" = false ]; then
        echo "[ERROR] Unable to locate ${helper_functions_file}"
        exit 1
    fi
}

_source_helper_file "package/common" "common_functions.sh"

# figure out where this script is being run from, accordingly set repo_root_path
if [ -f "WORKSPACE" ] || [ -f "MODULE.bazel" ]; then
    repo_root_path=`pwd`
else
    # "bazel run" sets the env var BUILD_WORKING_DIRECTORY, which points
    # to the root of the repository
    if [ -f "$BUILD_WORKING_DIRECTORY/WORKSPACE" ] || [ -f "$BUILD_WORKING_DIRECTORY/MODULE.bazel" ]; then
        # $BUILD_WORKING_DIRECTORY is set by "bazel run"
        repo_root_path=$BUILD_WORKING_DIRECTORY
        cd $repo_root_path
    else
        echo "[ERROR] This script must run from the repository root"
        exit 1
    fi
fi

# load config values
config_output=$(bazel run @poppy//misc:configvalueloader -- --key general.jspackage_base_filename)

# parse the output (values separated by |)
IFS='|' read -r package_base_filename <<< "$config_output"

_run_actions $actions $package_base_filename

#!/bin/bash

# Copyright (c) 2025, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

set -e

print_usage() {
cat << EOF

Usage: bazel run @poppy//package/py -a action(s) -l path/to/library/root/dir

  Required arguments:

  -a (actions)
    Specifies which action(s) to run, see below for detaols on the actions.
    Make sure you run 'gen' before trying other actions.
    The actions to run may be comma-separated if there is more than one,
    for example: -a gen,build

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
    gen: generates pyproject.toml files for the given library and upstream
         libraries.  IMPORTANT: this action is required to run at least once
         before any of the other actions.

    
  Other actions:
    build: runs "python3 -m build" on the given library and its upstreams.
           If the environment variable GLOBAL_DIST_DIR is set, also copies
           the content of the local dist directory, created by python3 -m
           build, to the directory $GLOBAL_DIST_DIR points to.
           
EOF
}


_for_each_pyproject() {
    local action=$1
    local repo_root=$2
    local pyproject_root_dir=$3
    local pyproject_filter_path=$4

    if ! [[ "$action" =~ ^(clean|build)$ ]]; then
        echo "ERROR: Unknown action $action" && exit 1
    fi

    if [ ! -d $pyproject_root_dir ]; then
        echo "ERROR: pyproject_root_dir does not exist: $pyproject_root_dir"
        exit 1
    fi

    # look for pyproject files
    find -L $pyproject_root_dir$pyproject_filter_path -name "pyproject.toml"|while read pyproject_path; do
        echo "INFO: Processing: $pyproject_path"

        if [ "$action" == "clean" ]; then
            rm $pyproject_path
        elif [ "$action" == "build" ]; then
            pyproject_rel_path="${pyproject_path#$pyproject_root_dir/}"
            pyproject_dest_dir=${repo_root}/${pyproject_rel_path}
            cp $pyproject_path $pyproject_dest_dir # cp into ws/source dir
            project_root_dir=$(dirname $pyproject_dest_dir)
            echo "INFO Running python3 -m build $project_root_dir"
            python3 -m build $project_root_dir
            if [ -z "$GLOBAL_DIST_DIR" ]; then
               echo "INFO GLOBAL_DIST_DIR is not set, not copying dist/*"
            else
                echo "INFO Copying dist/* to GLOBAL_DIST_DIR $GLOBAL_DIST_DIR"
                mkdir -p $GLOBAL_DIST_DIR
                cp -r $project_root_dir/dist/* $GLOBAL_DIST_DIR
            fi
        fi
    done
}

_run_actions() {
    local actions=$1
    for action in $(echo $actions | tr "," "\n")
    do
        if ! [[ "$action" =~ ^(clean|gen|build)$ ]]; then
            echo "[ERROR] action [$action] must be one of [clean|gen|build]" && exit 1
        fi

        repo_root=$PWD
        pyproject_root_dir=$repo_root/bazel-bin
        if [ ! -d $pyproject_root_dir ]; then
            echo "ERROR: bazel-bin doesn't exist, run `bazel build` on something."
           exit 1
        fi

        echo ""
        echo "Running action [$action]"
        echo ""

        if [ "$action" == "gen" ]; then
            local extra_args=""
            if [ "$debug" = true ]; then
                extra_args="${extra_args} --verbose"
            fi
            if [ "$force_gen" = true ]; then
                extra_args="${extra_args} --force"
            fi
            if [ "$follow_references" = false ]; then
                extra_args="${extra_args} --ignore_references"
            fi
            if [ "$debug" = true ]; then
                echo "[DEBUG] Running poppy with extra args ${extra_args}"
                extra_args="${extra_args} --verbose"
            fi
            bazel run @poppy//:gen -- --package $library_path --destdir $pyproject_root_dir $extra_args
        else
            # for now we constrain the path where we look for generated toml 
            # files - this won't work once we allow libraries referencing other
            # libraries
            _for_each_pyproject $action $repo_root $pyproject_root_dir $library_path
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
    echo "        $ bazel run @poppy//package/py -- -a gen,build"
    echo "        bazel run @poppy//package/py for usage information."
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

if [ "$debug" = true ]; then
    echo "[DEBUG] Running from directory: $(pwd)"
    echo "[DEBUG] Directory content: $(find . )"
    echo "[DEBUG] Environment: $(env)"
fi

# figure out where this script is being run from, accordingly set repo_root_path
if [ -f "WORKSPACE" ]; then
    repo_root_path=`pwd`
else
    # "bazel run" sets the env var BUILD_WORKING_DIRECTORY, which points
    # to the root of the repository
    if [ -f "$BUILD_WORKING_DIRECTORY/WORKSPACE" ]; then
        # $BUILD_WORKING_DIRECTORY is set by "bazel run"
        repo_root_path=$BUILD_WORKING_DIRECTORY
        cd $repo_root_path
    else
        echo "[ERROR] This script must run from the repository root"
        exit 1
    fi
fi

_run_actions "$actions"

#!/bin/bash

# Copyright (c) 2018, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

set -e

print_usage() {
cat << EOF

Usage: maven.sh -a action(s) [-l path/to/library]

  Required arguments:

  -a (actions)
    specifies which action(s) to run, see below for detaols on the actions.
    Make sure you run 'pomgen' before trying other actions.
    The actions to run may be comma-separated if there is more than one,
    for example: -a pomgen,install

  Optional arguments:

  -l (library path)
    library path - the relative path to the root directory of a library,
    defaults to all libraries in the repository
    For example: -l path/to/lib/dir (the dir that has MVN-INF/LIBRARY.root)

  -i (ignore references)
    by default, the library specified using -l is used as a starting point and
    upstream libraries are processed as well. This behavior can be disabled
    using -i

  -d (debug)
    enables debug logging

  -f (force)
    runs pomgen even if no changes to artifacts have been made

  -h (help)
    this message


  Mandatory action:
    pomgen: generates pom files for Maven artifacts.  IMPORTANT: this action
      is required to run at least once before any of the other actions.

    
  Additional supported actions:
    install: installs binary (jar) and pom artifacts into the local
      Maven repository.

    install_all: installs binary, sources, javadoc and pom artifacts into the
      local Maven repository.
      The sources jar is built by Bazel's java_library implicit
      lib<name>-src.jar target - if that target did not run and the sources
      jar does not exist, pomgen skips it.


    deploy_all: deploys binary, sources, javadoc and pom artifacts to Nexus.
      Uses credentials from ~/.m2/settings.xml's "default" server entry.
      The sources jar is built by Bazel's java_library implicit
      lib<name>-src.jar target - if that target did not run and the sources
      jar does not exist, pomgen skips it.

    deploy_only: re-attempts upload of all artifacts to Nexus.  Assumes
      "deploy_all" has run once.  This is useful for debugging upload issues.
      Uses credentials from ~/.m2/settings.xml's "default" server entry.


    clean: removes generated pom files and Maven build "target" directories 
      from the src tree.


    build: builds all libraries being processed (bazel build path/to/lib/...).
      pomgen expects all jars that will be uploaded or installed locally to
      exist - in case they do not, this action can be helpful.



  Supported environment variables:
    MVN_ARGS: may be used to pass additional arguments to Maven.
      For example to point to settings.xml in a non-standard location:
      export MVN_ARGS="--settings /my/path/to/settings.xml"

    REPOSITORY_URL: for the 2 deploy actions, the environment variable 
      REPOSITORY_URL must be set to the remote artifact repository to upload to.
      For example, when using Nexus:
          export REPOSITORY_URL=https://nexus.host/nexus/repository"
      Artifacts will either be uploaded to ${REPOSITORY_URL}/snapshots
      or ${REPOSITORY_URL}/releases, based on whether the artifact
      version ends in -SNAPTSHOT or not.

    REPOSITORY_ID: in settings.xml, the <id> of the <server> entry to use for
      authentication. Defaults to "nexus".
      See https://maven.apache.org/plugins/maven-deploy-plugin/deploy-file-mojo.html

    POM_DESCRIPTION: if set, used as the value of the <description> element
      in the generated pom(s).

    BZL_BUILD_WILDCARD: the 'build' action uses '...' as wildcard when building
      from the root of each library directory. This env var controls the
      wildcard to use, specifically in some cases it may be useful to use
      '...:all-targets' to include targets not built by default (such as
      _deploy.jar from java_binary rules)


  Examples (run from repository root):

  Generate poms for the hello-world example:

      bazel run @pomgen//maven -- -a pomgen -l examples/hello-world


  Install all example artifacts into the local Maven repository:
  
      bazel run @pomgen//maven -- -a install -l examples/hello-world


  Upload all examples, including javadoc and source jars, to Nexus:
  
      bazel run @pomgen//maven -- -a deploy_all


  More than one action may be specified, for example, to generate poms and
  then install to the local Maven repository:

      bazel run @pomgen//maven -- -a pomgen,install

EOF
}


_build_libraries_file_path() {
    local repo_root_path=$1
    local library=$2
    local libraries_file_path="$repo_root_path/bazel-bin$library/libraries.txt"
    echo "$libraries_file_path"
}


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
            local path="$(_build_libraries_file_path $repo_root_path $library_path)"
            if [ -f "$path" ]; then
                echo "true"
            else
                echo "false"
            fi
        fi
    fi
}


_for_each_library() {
    local action=$1
    local repo_root_path=$2
    local jar_artifact_classifier=$3
    local library_path=$4

    if ! [[ "$action" =~ ^(install|build)$ ]]; then
        echo "ERROR: Unknown action $action" && exit 1
    fi

    libraries_file_path="$(_build_libraries_file_path $repo_root_path $library_path)"
    echo "[INFO] libraries to process:"
    cat "$libraries_file_path"
    echo ""
    while read library_path;
    do
        echo "[INFO] Processing library: $library_path"
        if [ "$action" == "install" ]; then
          _for_each_pom "install_main_artifact" $repo_root_path $jar_artifact_classifier "/$library_path"
        elif [ "$action" == "build" ]; then
          local cmd="bazel build ${library_path}/${BZL_BUILD_WILDCARD:-"..."}"
          echo "[INFO] Running $cmd"
          $cmd
        fi
    done <<< "$(cat $libraries_file_path)"
}


if [ "$#" -eq 0 ]; then
  print_usage && exit 1
fi

library_path=""
force_pomgen=false
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
    f ) force_pomgen=true
    ;;
    i ) follow_references=false
    ;;
    h ) print_usage && exit 1
    ;;
    t ) echo "-t has been replaced by -l (-l path/to/library)" && exit 1
  esac
done

if [ "$debug" = true ]; then
    echo "[DEBUG] Debug logging enabled"
fi

if [ -z "$actions" ] ; then
    echo "[ERROR] The action(s) to run must be specified using -a, for example:"
    echo "        $ bazel run @pomgen//maven -- -a install"
    echo "        bazel run @pomgen//maven for usage information."
    exit 1
fi


if [ -z "$library_path" ] ; then
    echo "[INFO] No library specified, defaulting to 'all'"
    library_path="/."
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

# load helper functions
helper_functions_file="maven_functions.sh"
this_script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ -f "${this_script_dir}/${helper_functions_file}" ]; then
    # look relative to this file
    source "${this_script_dir}/${helper_functions_file}"
else
    # to support running through "bazel run", look in a few other places
    p="external/pomgen/maven/${helper_functions_file}"
    if [ -f "${p}" ]; then
        # remote repository
        source "${p}"
    else
        p="maven/${helper_functions_file}"
        if [ -f "${p}" ]; then
            # local pomgen repository
            source "${p}"
        else
            echo "[ERROR] Unable to locate ${helper_functions_file}" && exit 1
        fi
    fi
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


# load the configured classifier to use for jar artifacts, this classifier is
# used for jars processed below by this script, and it is added to generated
# pom.xml files referencing those jars
jar_artifact_classifier=$(bazel run @pomgen//misc:configvalueloader -- --key artifact.jar_classifier --default None)


for action in $(echo $actions | tr "," "\n")
do
    if ! [[ "$action" =~ ^(clean|pomgen|install|install_all|deploy_all|deploy_only|build)$ ]]; then
        echo "[ERROR] action [$action] must be one of [clean|install|install_all|deploy_all|deploy_only]" && exit 1
    fi

    echo ""
    echo "Running action [$action]"
    echo ""

    if [ "$action" == "clean" ]; then
        _for_each_pom "clean_source_tree" $repo_root_path $jar_artifact_classifier $library_path

    elif [ "$action" == "pomgen" ]; then
        extra_args=""
        if [ "$debug" = true ]; then
            extra_args="--verbose"
        fi
        if [ "$force_pomgen" = true ]; then
            extra_args="${extra_args} --force"
        fi
        if [ "$follow_references" = false ]; then
            extra_args="${extra_args} --ignore_references"
        fi
        if [ "$debug" = true ]; then
            echo "[DEBUG] Running with pomgen extra args ${extra_args}"
        fi
        bazel run @pomgen//:pomgen -- \
               --package $library_path \
               --destdir $repo_root_path/bazel-bin \
               --pom.description "${POM_DESCRIPTION:-""}" $extra_args


    elif [ "$action" == "install" ]; then
        if [ "$(_use_libraries_hint_file $repo_root_path $follow_references $library_path)" == "true" ]; then
            _for_each_library $action $repo_root_path $jar_artifact_classifier $library_path
        else
            _for_each_pom "install_main_artifact" $repo_root_path $jar_artifact_classifier $library_path
        fi

    elif [ "$action" == "install_all" ]; then
        # do not specify $library_path below because the javadoc maven plugin
        # looks for dependencies
        _for_each_pom "install_main_artifact" $repo_root_path $jar_artifact_classifier
        _for_each_pom "build_javadoc_jar" $repo_root_path $jar_artifact_classifier $library_path
        _for_each_pom "install_sources_and_javadoc_jars" $repo_root_path $jar_artifact_classifier $library_path

    elif [ "$action" == "deploy_all" ]; then
        if [ -z "$REPOSITORY_URL" ]; then
            echo "[ERROR] REPOSITORY_URL must be set"
            exit 1
        fi

        # no filter below because the javadoc maven plugin looks for
        # dependencies
        _for_each_pom "install_main_artifact" $repo_root_path $jar_artifact_classifier
        _for_each_pom "build_javadoc_jar" $repo_root_path $jar_artifact_classifier $library_path
        _for_each_pom "upload_all_artifacts" $repo_root_path $jar_artifact_classifier $library_path

    elif [ "$action" == "deploy_only" ]; then
        if [ -z "$REPOSITORY_URL" ]; then
            echo "[ERROR] REPOSITORY_URL must be set"
            exit 1
        fi
        _for_each_pom "upload_all_artifacts" $repo_root_path $jar_artifact_classifier $library_path

    elif [ "$action" == "build" ]; then
        if [ "$(_use_libraries_hint_file $repo_root_path $follow_references $library_path )" == "true" ]; then
        _for_each_library $action $repo_root_path $jar_artifact_classifier $library_path
        else
            echo "[ERROR] The 'build' action requires -l to point to a library"
            echo "        The 'pomgen' action must already have run for this library"
            echo "        Building is not supported with -i, you can just run"
            echo "        'bazel build' directly if you do not want to follow references"
            exit 1
        fi
    fi    
    
done

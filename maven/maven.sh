#!/bin/bash

# Copyright (c) 2018, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

set -e

print_usage() {
cat << EOF

Usage: maven.sh -a action(s) [-t bazel package]

  Required arguments:

  -a specifies which action(s) to run, see below.
    Make sure you run 'pomgen' before trying other actions.
    The actions to run may be comma-separated if there is more than one,
    for example: -a pomgen,install

  Optional arguments:

  -t specifies a bazel target pattern to run the action for.
    If not specified, it defaults to //...

  -d enables debug logging

  -f  


  Mandatory action:
    pomgen: generates pom files for Maven artifacts.  IMPORTANT: this action
      is required to run at least once before any of the other actions.
    
  Additional supported actions:
    install: installs the main binary artifacts (and poms) into the local
      Maven repository.
    install_all: installs binary, sources, javadoc and pom artifacts into the
      local Maven repository.

    deploy_all: deploys binary, sources, javadoc and pom artifacts to Nexus.
      Uses credentials from ~/.m2/settings.xml's "default" server entry.
    deploy_only: re-attempts upload of all artifacts to Nexus.  Assumes
      "deploy_all" has run once.  This is useful for debugging upload issues.
      Uses credentials from ~/.m2/settings.xml's "default" server entry.

    clean: removes generated pom files and Maven build "target" directories 
      from the src tree.


  Supported environment variables:
    MVN_ARGS: may be used to pass additional arguments to Maven.
      For example to point to settings.xml in a non-standard location:
      export MVN_ARGS="--settings /my/path/to/settings.xml"

    REPOSITORY_URL: for the 2 deploy actions, the environment variable 
      REPOSITORY_URL must be set to the remote artifact repository to upload to.
      For example, when using Nexus:
          export REPOSITORY_URL=https://nexus.host/nexus/service/local/repositories"
      Artifacts will either be uploaded to ${REPOSITORY_URL}/snapshots/content
      or ${REPOSITORY_URL}/releases/content, based on whether the artifact
      version ends in -SNAPTSHOT or not.

    POM_DESCRIPTION: if set, used as the value of the <description> element
      in the generated pom(s).


  Examples (run from repository root):

  Generate poms for all example artififacts:

      maven/maven.sh -a pomgen -t example


  Install all example artifacts into the local Maven repository:
  
      maven/maven.sh -a install -t example


  Upload all example, including javadoc and source jars, to Nexus:
  
      maven/maven.sh -a deploy_all


  More than one action may be specified, for example, to generate poms and
  then install to the local Maven repository:

      maven/maven.sh -a pomgen,install

EOF
}

if [ "$#" -eq 0 ]; then
  print_usage && exit 1
fi

debug=false
force_pomgen=false

while getopts "a:t:df" option; do
  case $option in
    a ) actions=$OPTARG
    ;;
    t ) target=$OPTARG
    ;;
    d ) debug=true
    ;;
    f ) force_pomgen=true
    ;;
  esac
done

if [ "$debug" = true ]; then
    echo "DEBUG: Debug logging enabled"
fi

if [ -z "$actions" ] ; then
    echo "ERROR: The action(s) to run must be specified using -a, for example:"
    echo "       $ maven/maven.sh -a install"
    echo "       Run maven.sh without arguments for usage information."
    exit 1
fi

# convert some simple Bazel target patterns to a path
if [[ $target == "//..." ]]; then
    # if filter is "//..." just unset it
    unset target
elif [[ $target == //* ]]; then
    # if it starts with "//", remove first '/'
    target=${target#*"/"}        
elif [[ $target != /* ]]; then
    # target needs to start with a '/'
    target=/$target
fi
if [[ $target == *... ]]; then
    # if target ends with '...', remove
    target=${target%"..."}        
fi
if [[ $target == */ ]]; then
    # if target ends with '/', remove
    target=${target%"/"}        
fi
if [[ $target == *:* ]]; then
    target=${target%:*}
fi
if [ -z "$target" ] ; then
    echo "INFO: No target specified, defaulting to //..."
    target="/."
fi

echo "INFO: Running ${actions} with target: ${target}"

if [ "$debug" = true ]; then
    echo "DEBUG: Running from directory: $(pwd)"
    echo "DEBUG: Directory content: $(find . )"
    echo "DEBUG: Environment: $(env)"
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
            echo "ERROR: Unable to locate ${helper_functions_file}" && exit 1
        fi
    fi
fi

# figure out where this script is being run from, accordingly set repo_root_path
if [ -f "WORKSPACE" ]; then
    repo_root_path=`pwd`
else
    # only necessary when running using "bazel run"
    if [ -f "$BUILD_WORKING_DIRECTORY/WORKSPACE" ]; then
        # $BUILD_WORKING_DIRECTORY is set by "bazel run"
        repo_root_path=$BUILD_WORKING_DIRECTORY
        cd $repo_root_path
    else
        echo "ERROR: please run this script from the repository root"
        exit 1
    fi
fi

for action in $(echo $actions | tr "," "\n")
do
    if ! [[ "$action" =~ ^(clean|pomgen|install|install_all|deploy_all|deploy_only)$ ]]; then
        echo "ERROR: action [$action] must be one of [clean|install|install_all|deploy|deploy_all|deploy_only]" && exit 1
    fi

    echo ""
    echo "Running action [$action]"
    echo ""

    if [ "$action" == "clean" ]; then
        _for_each_pom "clean_source_tree" $repo_root_path $target

    elif [ "$action" == "pomgen" ]; then
        extra_args=""
        if [ "$debug" = true ]; then
            extra_args="--verbose"
        fi
        if [ "$force_pomgen" = true ]; then
            extra_args="${extra_args} --force"
        fi
        if [ "$debug" = true ]; then
            echo "DEBUG: running with pomgen extra args ${extra_args}"
        fi
        bazel run @pomgen//:pomgen -- \
               --package $target \
               --destdir $repo_root_path/bazel-bin \
               --recursive \
               --pom.description "${POM_DESCRIPTION:-""}" $extra_args


    elif [ "$action" == "install" ]; then
        _for_each_pom "install_main_artifact" $repo_root_path $target

    elif [ "$action" == "install_all" ]; then
        # no filter below because the javadoc maven plugin looks for dependencies
        _for_each_pom "install_main_artifact" $repo_root_path
        _for_each_pom "build_sources_and_javadoc_jars" $repo_root_path $target
        _for_each_pom "install_sources_and_javadoc_jars" $repo_root_path $target

    elif [ "$action" == "deploy_all" ]; then
        if [ -z "$REPOSITORY_URL" ]; then
            echo "ERROR: REPOSITORY_URL must be set"
            exit 1
        fi

        # no filter below because the javadoc maven plugin looks for dependencies
        _for_each_pom "install_main_artifact" $repo_root_path
        _for_each_pom "build_sources_and_javadoc_jars" $repo_root_path $target
        _for_each_pom "upload_all_artifacts" $repo_root_path $target


    elif [ "$action" == "deploy_only" ]; then
        if [ -z "$REPOSITORY_URL" ]; then
            echo "ERROR: REPOSITORY_URL must be set"
            exit 1
        fi
        _for_each_pom "upload_all_artifacts" $repo_root_path $target
    fi
    
done

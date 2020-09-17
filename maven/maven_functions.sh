# Copyright (c) 2018, salesforce.com, inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
# For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause

# 1st arg: action to run for each pom found in the build directory
# 2nd arg: path to root of repo
# 3rd arg: optional relative repo path for a more targeted pom search, must start with a '/'
_for_each_pom() {
    action=$1
    repo_root_dir_path=$2
    pom_root_path=$3

    if ! [[ "$action" =~ ^(install_main_artifact|build_sources_and_javadoc_jars|install_sources_and_javadoc_jars|upload_all_artifacts|clean_source_tree)$ ]]; then
        echo "ERROR: Unknown action $action" && exit 1
    fi

    repo_build_dir_path=$repo_root_dir_path/bazel-bin

    if [ ! -d $repo_build_dir_path ]; then
        echo "ERROR: Root build directory not found: $repo_build_dir_path"
        echo "       Build the repository before running this script."
        exit 1
    fi

    abs_pom_root_path=$repo_build_dir_path$pom_root_path

    find -L $abs_pom_root_path -name "pom.xml"|while read pom_path; do
        echo "INFO: Processing pom: $pom_path"
        build_dir_package_path="$(dirname "$pom_path")"
        src_dir_rel_path=${build_dir_package_path#$repo_build_dir_path}
        src_dir_package_path=$repo_root_dir_path$src_dir_rel_path
        package_name=$(basename "$src_dir_package_path")

        # the location of javadoc and sources jars
        target_dir_path="$src_dir_package_path/target"

        # run clean early, before any validation logic may cause an error
        if [ "$action" == "clean_source_tree" ]; then
            rm $pom_path
            rm -rf $target_dir_path
            continue
        fi

        # determine what kind of artifact (packaging) we are dealing with -
        # we support jar, pom and maven-plugin, but we really only distinguish
        # between pom and "others"
        is_pom_only_artifact=0

        # whether we should process (add pom etc) the jar artifact before
        # uploading it to Nexus
        process_jar_artifact=1

        # look for "<packaging> in the pom file
        pom_packaging=$(grep "<packaging>" $pom_path || true)
        if [ -z "$pom_packaging" ]; then
            echo "ERROR: pom doesn't specify its packaging: $pom_path"
            echo ""
            echo "You may have to run tools/maven/maven.sh -a clean to remove"
            echo "stale poms (you will have to re-run pomgen)"
            echo ""
            exit 1
        fi

        res=$(echo $pom_packaging | grep "pom" || true)
        if [ -z "$res" ]; then
            is_pom_only_artifact=0
            process_jar_artifact=1
        else
            is_pom_only_artifact=1
            process_jar_artifact=0
        fi

        # sets ARTIFACT_ID, GROUP_ID, VERSION for the pom being processed
        _get_maven_coordinates $pom_path
        echo "INFO: Parsed Maven coordinates ${GROUP_ID}:${ARTIFACT_ID}:${VERSION}"

        if [ "$is_pom_only_artifact" == 0 ]; then
            # determine the jar file name bazel built:
            # we'll use the package name, which follows our java_library target
            # naming convention - this could be made configurable in the
            # BUILD.pom file if necessary

            # the filename of the jar built by Bazel uses this pattern:
            jar_artifact_path="$build_dir_package_path/lib${package_name}.jar"
            if [ ! -f "${jar_artifact_path}" ]; then
                echo "WARN: lib${package_name}.jar not found, looking for alternatives"
                # we also support executable jars - this is an edge case but
                # there are use-cases where it is convenient to be able to
                # upload a "uber jar" to Nexus instead of building a docker
                # image for it

                # first we look for the special <target-name>_deploy.jar
                # created by java_binary
                jar_artifact_path="$build_dir_package_path/${package_name}_deploy.jar"
                if [ -f "${jar_artifact_path}" ]; then
                    echo "INFO: Found ${package_name}_deploy.jar"
                else
                    # last attempt: maybe a jar called <target-name>.jar
                    # exists
                    jar_artifact_path="$build_dir_package_path/${package_name}.jar"
                    if [ -f "${jar_artifact_path}" ]; then
                        echo "INFO: Found ${package_name}.jar"
                    fi
                fi
                # we've seen jar break in weird ways when trying to unjar large
                # "uber" jars:
                # java.io.FileNotFoundException: META-INF/LICENSE (Is a directory)
                # disable unjaring in order to add the generated pom to the jar,
                # which isn't that important for uber jars (not used as deps)
                # anyway
                process_jar_artifact=0
            fi
            if [ ! -f "${jar_artifact_path}" ]; then
                echo "ERROR: did not find jar artifact at ${jar_artifact_path}"
                echo "This is a bug"
                exit 1
            fi

            if [ -d "$target_dir_path" ]; then
                sources_jar_path=$(find "$target_dir_path" -name "*$VERSION-sources.jar"||true)
                javadoc_jar_path=$(find "$target_dir_path" -name "*$VERSION-javadoc.jar"||true)
            fi
        fi

        if [ "$process_jar_artifact" == 1 ]; then
            _add_pom_to_jar\
                $pom_path $jar_artifact_path $GROUP_ID $ARTIFACT_ID $VERSION
            jar_artifact_path=$UPDATED_JAR_ARTIFACT_PATH
        fi

        if [ "$action" == "install_main_artifact" ]; then
            _install_artifact $pom_path $jar_artifact_path

        elif [ "$action" == "build_sources_and_javadoc_jars" ]; then
            if [ "$is_pom_only_artifact" == 1 ]; then
                echo "INFO: Skipping sources/javadoc building for pom-only artifact"
            else
                _build_source_and_javadoc_jars $pom_path $src_dir_package_path
            fi

        elif [ "$action" == "install_sources_and_javadoc_jars" ]; then
            if [ "$is_pom_only_artifact" == 1 ]; then
                echo "INFO: Skipping sources/javadoc installing for pom-only artifact"
            else
                _install_artifact $pom_path $sources_jar_path "sources"
                _install_artifact $pom_path $javadoc_jar_path "javadoc"
            fi

        elif [ "$action" == "upload_all_artifacts" ]; then
            _deploy_artifacts_to_nexus \
                $pom_path \
                $VERSION \
                $jar_artifact_path \
                $sources_jar_path \
                $javadoc_jar_path
        fi

        unset jar_artifact_path
        unset target_dir_path
        unset sources_jar_path
        unset javadoc_jar_path

        unset GROUP_ID
        unset ARTIFACT_ID
        unset VERSION
        unset UPDATED_JAR_ARTIFACT_PATH

        echo "INFO: Finished processing pom: $pom_path"
        echo ""

    done
}

# 1st arg: path to pom file
# 2nd arg: path to jar artifact (optional if pom only)
# 3rd arg: classifier (optional)
_install_artifact() {
    pom_path=$1
    artifact_path=$2
    classifier=$3

    if [ -z "$artifact_path" ]; then
        echo "INFO: Installing pom only to local repository: $pom_path"
        artifact_path=$pom_path
    else
        # it is possible (though rare) that jar artifacts do not contain Java
        # source code, in which case they don't have srcs/javadoc jars either
        if [ ! -f "$artifact_path" ]; then
            echo "INFO: Artifact not found, skipping \"$artifact_path\" for pom $pom_path"
            return
        else
            echo "INFO: Installing artifact to local repository: $artifact_path"
        fi
    fi

    if [ -z "${classifier}" ]; then
        unset classifier_arg
    else
        classifier_arg="-Dclassifier=$classifier"
    fi

    mvn ${MVN_ARGS} org.apache.maven.plugins:maven-install-plugin:2.5.2:install-file \
        -DpomFile=$pom_path -Dfile=$artifact_path $classifier_arg
}

# copies pom into the src tree (because that's where the sources happen to be)
# 1st arg: path to pom
# 2nd arg: path to Bazel package to copy the pom into
_build_source_and_javadoc_jars() {
    pom_path=$1
    src_dir_package_path=$2

    src_dir_pom_path="$src_dir_package_path/pom.xml"
    echo "INFO: Generating javadoc and sources jars at $src_dir_package_path"
    cp -f $pom_path $src_dir_pom_path
    # we run with -Dmaven.javadoc.failOnError=false because javadoc errros
    # are not a big deal, in the grand scheme of things - and lets be honest
    # nobody actually ever looks at javadoc anyway
    mvn ${MVN_ARGS} -Dmaven.javadoc.failOnError=false -f $src_dir_pom_path source:jar javadoc:jar
    rm -f $src_dir_pom_path
}

# 1st arg: path to pom file
# 2nd arg: the artifact version to deploy
# 3rd arg: path to artifact to deploy (optional)
# 4rd arg: javadoc artifact path (optional)
# 5rd arg: sources artifact path (optional)
_deploy_artifacts_to_nexus() {
    pom_path=$1
    version=$2
    artifact_path=$3
    sources_artifact_path=$4
    javadoc_artifact_path=$5

    if [ -z "$REPOSITORY_URL" ]; then
        echo "ERROR: REPOSITORY_URL must be set"
        exit 1
    fi

    if [[ "$version" = *"-SNAPSHOT" ]]; then
        repository="snapshots"
    else
        repository="releases"
    fi

    full_repository_url=${REPOSITORY_URL}/${repository}/content

    if [ -z "$artifact_path" ]; then
        artifact_path=$pom_path
        unset file_arg
        unset type_arg
        unset classifier_arg
    else
        if [ -f "${sources_artifact_path}" ] && [ -f "${javadoc_artifact_path}" ]; then
            file_arg="-Dfiles=${sources_artifact_path},${javadoc_artifact_path}"
            type_arg="-Dtypes=jar,jar"
            classifier_arg="-Dclassifiers=sources,javadoc"

        # it is possible (though rare) that jar artifacts do not contain
        # Java source code, in which case they don't have srcs/javadoc
        # jars either
        elif [ -f "${sources_artifact_path}" ]; then
            file_arg="-Dfiles=${sources_artifact_path}"
            type_arg="-Dtypes=jar"
            classifier_arg="-Dclassifiers=sources"
        elif [ -f "${javadoc_artifact_path}" ]; then
            file_arg="-Dfiles=${javadoc_artifact_path}"
            type_arg="-Dtypes=jar"
            classifier_arg="-Dclassifiers=javadoc"
        else
            unset file_arg
            unset type_arg
            unset classifier_arg
        fi
    fi

    echo "INFO: Uploading to repository: $full_repository_url"
    echo "INFO: Uploading pom: $pom_path"
    echo "INFO: Uploading main artifact: $artifact_path"
    echo "INFO: Uploading other artifacts: ${sources_artifact_path} ${javadoc_artifact_path}"

    mvn ${MVN_ARGS} org.apache.maven.plugins:maven-deploy-plugin:2.8.2:deploy-file \
        -DpomFile=$pom_path \
        -Dfile=$artifact_path \
        -DrepositoryId="default" \
        -Durl=$full_repository_url \
        $file_arg $type_arg $classifier_arg
}

# parses artifactId, groupId and version out of the specified pom file
# sets the env vars ARTIFACT_ID, GROUP_ID and VERSION
# 1st arg: path to pom file
_get_maven_coordinates() {
    pom_path=$1
    ARTIFACT_ID=$(cat $pom_path | xmllint --format - | sed 's/project xmlns=".*"/project/g' | xmllint --xpath '/project/artifactId/text()' - || true)
    GROUP_ID=$(cat $pom_path | xmllint --format - | sed 's/project xmlns=".*"/project/g' | xmllint --xpath '/project/groupId/text()' - || true)
    VERSION=$(cat $pom_path | xmllint --format - | sed 's/project xmlns=".*"/project/g' | xmllint --xpath '/project/version/text()' - || true)

    if [ -z "$ARTIFACT_ID" ]; then
        echo "ERROR: failed to get artifactId out of $pom_path:"
        head $pom_path
        exit 1
    fi

    if [ -z "$GROUP_ID" ]; then
        echo "ERROR: failed to get groupId out of $pom_path:"
        head $pom_path
        exit 1
    fi

    if [ -z "$VERSION" ]; then
        echo "ERROR: failed to get version out of $pom_path:"
        head $pom_path
        exit 1
    fi
}

# adds the given pom file to the specied jar, at
# META-INF/<groupId>/<artifactId>/pom.xml
# also adds a META-INF/<groupId>/<artifactId>/pom.properties, with artifactId,
# groupId, version (another file Maven creates).
#
# sets the env var JAR_ARTIFACT_PATH to the update jar path
#
# 1st arg: path to pom file
# 2nd arg: path to jar artifact
# 3rd arg: groupId
# 4th arg: artifactId
# 5th arg: version
_add_pom_to_jar() {
    pom_path=$1
    artifact_path=$2
    group_id=$3
    artifact_id=$4
    version=$5

    root_tmpdir="$(dirname $jar_artifact_path)"
    meta_inf_relpath="META-INF/$group_id/$artifact_id"
    meta_inf_tmpdir="$root_tmpdir/$meta_inf_relpath"

    mkdir -p $meta_inf_tmpdir
    cp -f $pom_path $meta_inf_tmpdir

    pfile=$meta_inf_tmpdir/pom.properties
    cat >$pfile <<EOL
# Built by Bazel
# $(date)
version=${version}
groupId=${group_id}
artifactId=${artifact_id}
EOL
    # %???? removes the last 4 characters (.jar)
    new_artifact_path="${artifact_path%????}_withpom.jar"
    cp -f $artifact_path $new_artifact_path

    here=$(pwd)
    cd $root_tmpdir
    jar uf $new_artifact_path $meta_inf_relpath/*

    # update all timestamps inside the jar because the 0 timestamp set by Bazel
    # can cause problems, depending on what TZ this script runs in
    # Exception in thread "main" java.time.DateTimeException: Invalid value for MonthOfYear (valid values 1 - 12): 0
    mkdir extract
    cd extract
    jar xf $new_artifact_path
    find . | xargs touch
    jar cf $new_artifact_path *
    cd ..
    rm -rf extract

    cd $here
    rm -rf "$root_tmpdir/META-INF"

    UPDATED_JAR_ARTIFACT_PATH=$new_artifact_path
}

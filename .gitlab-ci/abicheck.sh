#! /bin/bash

set -ex
set -o pipefail

cihomedir=$(dirname "$0")
shift
basedir=$(realpath "$cihomedir/..")
newbuilddir=${1-$(realpath "$basedir/build")}
basebuilddir=$(realpath "$basedir/.build.base")

clean_exit() {
    rc=$?
    curbranch=$(git rev-parse --abbrev-ref HEAD)
    if [ -d "$basebuilddir" ]; then
        if git worktree list --porcelain | grep -q "$basebuilddir"; then
            git worktree remove -f "$basebuilddir"
            git branch -D "abicheck_main_$curbranch"
        fi
    fi
    exit $rc
}


copyresult() {
    dir="$1"
    tag="$2"
    if [ -f "$dir"/libfontconfig.so ]; then
        cp -L "$dir"/libfontconfig.so "$dir/libfontconfig-$tag.so"
    elif [ -f "$dir"/src/.libs/libfontconfig.so ]; then
        cp -L "$dir/src/.libs/libfontconfig-$tag.so" "$dir/libfontconfig-$tag.so"
    else
        echo "No fontconfig library built"
        exit 1
    fi
}

trap clean_exit INT TERM ABRT EXIT

if [ ! "$(command -v abidiff)" ]; then
    echo "No abidiff installed."
    exit 1
fi

# assume that the targeted build directory is up-to-date.
if [ ! -d "$newbuilddir" ]; then
    buildcmd=(python3 $cihomedir/build.py)
    if [ ! -f "$cihomedir/build.py" ]; then
        buildcmd=($cihomedir/build.sh)
    else
        buildcmd=(python3 $cihomedir/build.py)
    fi
    ${buildcmd[@]} "$@"
fi
copyresult "$newbuilddir" "new"

curbranch=$(git rev-parse --abbrev-ref HEAD)
if [ -d "$basebuilddir" ]; then
    if git worktree list --porcelain | grep -q "$basebuilddir"; then
        git worktree remove -f "$basebuilddir"
        git branch -D "abicheck_main_$curbranch"
    fi
fi
# Determine the ABI baseline to diff against:
#  - In CI merge-request pipelines, use the diff base (the commit this branch
#    diverged from the target) fetched from the target project.  This works
#    whether the pipeline runs on the upstream repo or a fork, and regardless
#    of how the target branch is named -- unlike a hardcoded "origin main",
#    which breaks on forks whose default branch is not "main".
#  - Otherwise (local runs, or non-MR pipelines) fall back to origin's main,
#    overridable via FC_ABI_BASELINE, so developers can still run this by hand.
if [ -n "$CI_MERGE_REQUEST_DIFF_BASE_SHA" ]; then
    baseref="$CI_MERGE_REQUEST_DIFF_BASE_SHA"
    git cat-file -e "$baseref^{commit}" 2>/dev/null \
        || git fetch "${CI_MERGE_REQUEST_PROJECT_URL:?}.git" "$baseref"
else
    git fetch origin "${FC_ABI_BASELINE:-main}"
    baseref=FETCH_HEAD
fi

git worktree add -b "abicheck_main_$curbranch" "$basebuilddir" "$baseref"
pushd "$basebuilddir"
if [ ! -f "$cihomedir/build.py" ]; then
    buildcmd=($cihomedir/build.sh)
else
    buildcmd=(python3 $cihomedir/build.py)
fi
# Do not run unit tests because main branch should be passed by CI
BUILDLOG="$newbuilddir/fc-basebuild.log" BUILDDIR="$basebuilddir/build" ${buildcmd[@]} -C "$@"
popd

copyresult "$basebuilddir/build" "old"
cp -L "$basebuilddir/build/libfontconfig-old.so" "$newbuilddir"

abidiff --no-added-syms --suppressions $cihomedir/.abidiff "$newbuilddir/libfontconfig-old.so" "$newbuilddir/libfontconfig-new.so" | python3 ./.gitlab-ci/abidiff2xml.py -o "$newbuilddir/abidiff.xml" -

#!/bin/sh
# fontconfig/autogen.sh
#
# Copyright © 2000 Keith Packard
#
# Permission to use, copy, modify, distribute, and sell this software and its
# documentation for any purpose is hereby granted without fee, provided that
# the above copyright notice appear in all copies and that both that
# copyright notice and this permission notice appear in supporting
# documentation, and that the name of the author(s) not be used in
# advertising or publicity pertaining to distribution of the software without
# specific, written prior permission.  The authors make no
# representations about the suitability of this software for any purpose.  It
# is provided "as is" without express or implied warranty.
#
# THE AUTHOR(S) DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO
# EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
# DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

# Run this to generate all the initial makefiles, etc.

set -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.

case "$1" in
--noconf*) 
    	AUTOGEN_SUBDIR_MODE="true"
	shift
	;;
esac

ORIGDIR=`pwd`
cd $srcdir
PROJECT=Fontconfig
TEST_TYPE=-f
FILE=fontconfig/fontconfig.h.in
LIBTOOLIZE=${LIBTOOLIZE-libtoolize}
AUTOPOINT=${AUTOPOINT-autopoint}
AUTORECONF=${AUTORECONF-autoreconf}
AUTORECONF_FLAGS=${AUTORECONF_FLAGS-"-i"}
GPERF=${GPERF-gperf}
GETTEXTIZE=${GETTEXTIZE-gettextize}
GETTEXTIZE_FLAGS="--force --no-changelog"

DIE=0

($GPERF --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have gperf installed to compile $PROJECT."
	echo "Install the appropriate package for your distribution."
	echo "or get the source tarball at ftp://ftp.gnu.org/pub/gnu/"
	DIE=1
}

have_libtool=false
if $LIBTOOLIZE --version < /dev/null > /dev/null 2>&1 ; then
	libtool_version=`$LIBTOOLIZE --version | sed 's/^.* \([0-9][.][0-9.]*\)[^ ]*$/\1/'`
	case $libtool_version in
	    1.4*|1.5*|1.6*|1.7*|2*)
		have_libtool=true
		;;
	esac
fi
if $have_libtool ; then : ; else
	echo
	echo "You must have libtool 1.4 installed to compile $PROJECT."
	echo "Install the appropriate package for your distribution,"
	echo "or get the source tarball at ftp://ftp.gnu.org/pub/gnu/"
	DIE=1
fi
($GETTEXTIZE --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have gettext installed to compile $PROJECT."
	echo "Install the appropriate package for your distribution,"
	echo "or get the source tarball at  ftp://ftp.gnu.org/pub/gnu/"
	DIE=1
}
($AUTOPOINT --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have autopoint installed to compile $PROJECT."
	echo "Install the appropriate package for your distribution,"
	echo "or get the source tarball at ftp://ftp.gnu.org/pub/gnu/"
	DIE=1
}
($AUTORECONF --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have autoreconf installed to compile $PROJECT."
	echo "Install the appropriate package for your distribution,"
	echo "or get the source tarball at ftp://ftp.gnu.org/pub/gnu/"
	DIE=1
}

if test "$DIE" -eq 1; then
	exit 1
fi

test $TEST_TYPE $FILE || {
	echo "You must run this script in the top-level $PROJECT directory"
	exit 1
}

if test -z "$AUTOGEN_SUBDIR_MODE" -a -z "$NOCONFIGURE"; then
        if test -z "$*"; then
                echo "I am going to run ./configure with no arguments - if you wish "
                echo "to pass any to it, please specify them on the $0 command line."
        fi
fi

echo Running $AUTORECONF $AUTORECONF_FLAGS
$AUTORECONF $AUTORECONF_FLAGS

cd $ORIGDIR

if test -z "$AUTOGEN_SUBDIR_MODE" -a -z "$NOCONFIGURE"; then
	echo Running $srcdir/configure "$@"
        $srcdir/configure "$@"

        echo 
        echo "Now type 'make' to compile $PROJECT."
fi

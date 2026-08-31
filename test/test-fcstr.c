/* Copyright (C) 2025 fontconfig Authors */
/* SPDX-License-Identifier: HPND */

/* Unit tests for functions in src/fcstr.c. */
#include "fcint.h"
#include <stdio.h>
#include <string.h>

/* FcStrListNext() must tolerate a NULL list argument (e.g. resulting from
 * a failed FcStrListCreate()) and return NULL instead of dereferencing it. */
static int
test_strlist_next_null (void)
{
    if (FcStrListNext (NULL) != NULL) {
	printf ("FcStrListNext(NULL) did not return NULL\n");
	return 1;
    }
    return 0;
}

/* FcStrCanonFilename() must tolerate a NULL argument (e.g. resulting from a
 * failed allocation in a caller) and return NULL instead of dereferencing it.
 * A valid absolute path must still be canonicalized as before. */
static int
test_canon_filename (void)
{
    FcChar8          *r;
    const char       *expected = "/foo/baz";
    size_t            rlen, elen;

    if (FcStrCanonFilename (NULL) != NULL) {
	printf ("FcStrCanonFilename(NULL) did not return NULL\n");
	return 1;
    }

    r = FcStrCanonFilename ((const FcChar8 *)"/foo/./bar/../baz");
    if (!r) {
	printf ("FcStrCanonFilename() failed on a valid path\n");
	return 1;
    }
    /* The . and .. squashing is portable, but on Windows GetFullPathName()
     * anchors a leading-slash path to the current drive (e.g. C:/foo/baz),
     * so only require the canonicalized tail to match. */
    rlen = strlen ((const char *)r);
    elen = strlen (expected);
    if (rlen < elen || strcmp ((const char *)r + rlen - elen, expected) != 0) {
	printf ("unexpected canonicalization: %s (expected tail %s)\n", r, expected);
	FcStrFree (r);
	return 1;
    }
    FcStrFree (r);

    return 0;
}

int
main (void)
{
    if (test_strlist_next_null () != 0)
	return 1;
    if (test_canon_filename () != 0)
	return 1;

    return 0;
}

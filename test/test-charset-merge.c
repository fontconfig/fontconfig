/* Copyright (C) 2026 fontconfig Authors */
/* SPDX-License-Identifier: HPND */

/*
 * Regression test for an out-of-bounds access in FcCharSetMerge().
 *
 * Page numbers in a charset are 16-bit, so 0xffff (covering the characters
 * U+FFFF00..U+FFFFFF) is a legitimate page.  FcCharSetMerge() used ~0 cast to
 * FcChar16 (== 0xffff) as the "a is exhausted" sentinel, so when b carried a
 * 0xffff page and a had run out of leaves, the sentinel compared equal to the
 * real page and the merge unioned into FcCharSetLeaf(a, a->num) -- one past the
 * end of a's leaves array.  A font with such a cmap entry could therefore crash
 * any caller that sorts fonts (FcFontSort / FcFontSetSort).
 *
 * These cases exercise the merge directly, with no font file required.
 */

#include <fontconfig/fontconfig.h>

#include <stdio.h>
#include <stdlib.h>

/* Highest page (0xffff) == the value that used to collide with the sentinel. */
#define TOP_PAGE_CHAR 0xffff42

static int
check (const char *name, FcCharSet *a, FcCharSet *b)
{
    FcBool changed = FcFalse;

    /* Without the fix this reads/writes past the end of a's leaves array. */
    if (!FcCharSetMerge (a, b, &changed)) {
	fprintf (stderr, "%s: FcCharSetMerge failed\n", name);
	return 1;
    }
    if (!changed) {
	fprintf (stderr, "%s: expected changed == FcTrue\n", name);
	return 1;
    }
    if (!FcCharSetHasChar (a, TOP_PAGE_CHAR)) {
	fprintf (stderr, "%s: merged charset is missing U+%06X\n",
	         name, (unsigned)TOP_PAGE_CHAR);
	return 1;
    }
    return 0;
}

int
main (void)
{
    FcCharSet *a, *b;
    int        ret = 0;

    /* Case 1: a is empty, b holds only the top page. */
    a = FcCharSetCreate ();
    b = FcCharSetCreate ();
    FcCharSetAddChar (b, TOP_PAGE_CHAR);
    ret |= check ("empty-a", a, b);
    FcCharSetDestroy (a);
    FcCharSetDestroy (b);

    /* Case 2: a runs out before b's top page (a has only a lower page). */
    a = FcCharSetCreate ();
    b = FcCharSetCreate ();
    FcCharSetAddChar (a, 0x41);
    FcCharSetAddChar (b, 0x41);
    FcCharSetAddChar (b, 0x5000);
    FcCharSetAddChar (b, TOP_PAGE_CHAR);
    ret |= check ("short-a", a, b);
    if (!FcCharSetHasChar (a, 0x5000)) {
	fprintf (stderr, "short-a: merged charset is missing U+5000\n");
	ret = 1;
    }
    FcCharSetDestroy (a);
    FcCharSetDestroy (b);

    /* Case 3: both a and b already carry the top page (union in place). */
    a = FcCharSetCreate ();
    b = FcCharSetCreate ();
    FcCharSetAddChar (a, TOP_PAGE_CHAR);
    FcCharSetAddChar (b, 0xffff01);
    ret |= check ("shared-top", a, b);
    if (!FcCharSetHasChar (a, 0xffff01)) {
	fprintf (stderr, "shared-top: merged charset is missing U+FFFF01\n");
	ret = 1;
    }
    FcCharSetDestroy (a);
    FcCharSetDestroy (b);

    FcFini ();

    if (ret == 0)
	printf ("PASS\n");
    return ret;
}

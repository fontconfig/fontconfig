/* Copyright (C) 2025 fontconfig Authors */
/* SPDX-License-Identifier: HPND */

/* Regression test for foundry extraction from the OS/2 achVendID.
 * no_family_name.ttf carries achVendID "GOOG", a full 4-byte OpenType
 * Tag, so this also exercises the NUL-termination boundary of the
 * fixed-size foundry buffer in FcFreeTypeQueryFace(). */
#include <fontconfig/fontconfig.h>
#include <fontconfig/fcfreetype.h>
#include <stdio.h>
#include <string.h>

int
main (void)
{
    FcPattern *pat;
    FcChar8   *foundry = NULL;
    int        count = 0;
    int        ret = 0;

    pat = FcFreeTypeQuery ((const FcChar8 *)FONTFILE, 0, NULL, &count);
    if (!pat) {
	fprintf (stderr, "failed to query %s\n", FONTFILE);
	return 1;
    }
    if (FcPatternGetString (pat, FC_FOUNDRY, 0, &foundry) != FcResultMatch) {
	fprintf (stderr, "no foundry in pattern\n");
	ret = 1;
    } else if (strcmp ((const char *)foundry, "GOOG") != 0) {
	fprintf (stderr, "unexpected foundry: %s (expected GOOG)\n", foundry);
	ret = 1;
    }
    FcPatternDestroy (pat);
    FcFini ();

    return ret;
}

/* Copyright (C) 2026 fontconfig Authors */
/* SPDX-License-Identifier: HPND */

/*
 * Unit test for the FC_SPACING classifier (FcSpacingClassify).
 *
 * The classifier is name-independent and runs in two stages:
 *   1. the legacy rule (single width -> MONO; two widths in a 2:1 ratio ->
 *      DUAL) is reproduced verbatim, so nothing that already had a spacing is
 *      reclassified;
 *   2. only when the legacy rule yields PROPORTIONAL do we attempt grid-based
 *      recovery, and only for fonts that monospace their ASCII letters.
 *
 * The cases mirror a real-font corpus measured on a live system (see the
 * monospace-detection plan).  They assert:
 *   - genuine grid fonts with a few intentionally wide glyphs (Noto Sans Mono,
 *     Latin Modern Mono) are recovered as MONO;
 *   - proportional-by-design fonts stay PROPORTIONAL even when named "Mono";
 *   - uniform full-width scripts / emoji / symbol fonts (grid-conformant but no
 *     monospaced ASCII) are NOT promoted;
 *   - fonts the legacy rule already recognised (incl. CJK dual) are preserved.
 */
#include "fcint.h"

#include <fontconfig/fontconfig.h>
#include <stdio.h>

typedef struct _SpacingCase
{
    const char *name;
    int         value[8];
    int         count[8];
    int         num;
    FcBool      overflow;
    FcBool      ascii_monospaced;
    int         expected;
} SpacingCase;

static int
total_of (const SpacingCase *c)
{
    int i, total = 0;
    for (i = 0; i < c->num; i++)
	total += c->count[i];
    return total;
}

static const char *
spacing_name (int spacing)
{
    switch (spacing) {
    case FC_SPACING_PROPORTIONAL: return "PROPORTIONAL";
    case FC_SPACING_DUAL: return "DUAL";
    case FC_SPACING_MONO: return "MONO";
    case FC_SPACING_CHARCELL: return "CHARCELL";
    default: return "?";
    }
}

static const SpacingCase cases[] = {
    /* name                               values                    counts                     n  ovf      ascii    expected */

    /* Legacy stage: no advances / one uniform width -> MONO (ASCII irrelevant). */
    { "empty",                            { 0 },                    { 0 },                     0, FcFalse, FcFalse, FC_SPACING_MONO },
    { "single width",                     { 600 },                  { 1000 },                  1, FcFalse, FcTrue,  FC_SPACING_MONO },
    { "Liberation Mono",                  { 1229 },                 { 1000 },                  1, FcFalse, FcTrue,  FC_SPACING_MONO },
    { "IBM Plex Mono",                    { 600 },                  { 5000 },                  1, FcFalse, FcTrue,  FC_SPACING_MONO },
    /* Legacy stage: two widths in 2:1 -> DUAL, preserved even without ASCII
     * (mirrors Droid Sans Japanese: half/full-width CJK, no Latin). */
    { "CJK dual, no ASCII (legacy)",      { 128, 256 },             { 63, 6555 },              2, FcFalse, FcFalse, FC_SPACING_DUAL },

    /* Recovery stage: grid fonts with intentionally wide glyphs and monospaced
     * ASCII -> MONO.  The legacy rule wrongly rejected these. */
    { "Noto Sans Mono (99.97%)",          { 563, 1126, 800 },       { 9994, 3, 3 },            3, FcFalse, FcTrue,  FC_SPACING_MONO },
    { "Latin Modern Mono (99.44%)",       { 525, 1050, 300 },       { 9944, 50, 6 },           3, FcFalse, FcTrue,  FC_SPACING_MONO },

    /* The ASCII gate is the decider between these two: identical uniform
     * full-width grid, promoted only when the ASCII is monospaced. */
    { "full-width grid, ASCII mono",      { 1000, 2000, 3000 },     { 9800, 150, 50 },         3, FcFalse, FcTrue,  FC_SPACING_MONO },
    { "full-width grid, no ASCII (CJK)",  { 1000, 2000, 3000 },     { 9800, 150, 50 },         3, FcFalse, FcFalse, FC_SPACING_PROPORTIONAL },

    /* Recovery stage, rejected on grid conformance (ASCII is monospaced). */
    { "Latin Modern Mono Prop (27%)",     { 261, 400, 550, 700 },   { 270, 250, 240, 240 },    4, FcFalse, FcTrue,  FC_SPACING_PROPORTIONAL },
    { "Noto Sans Mono CJK (73%)",         { 1000, 500, 920 },       { 6000, 1300, 2700 },      3, FcFalse, FcTrue,  FC_SPACING_PROPORTIONAL },
    /* One dominant width (94.9%) + scattered tail (mirrors AlgolRevived): the
     * tail sits on a 63 (W/2) grid, so a half-width candidate would wrongly
     * promote it; whole-cluster candidates keep it proportional. */
    { "single width + scattered tail",    { 126, 190, 310, 440, 570, 695, 820 }, { 9190, 100, 90, 85, 80, 75, 61 }, 7, FcFalse, FcTrue, FC_SPACING_PROPORTIONAL },

    /* Recovery stage, rejected by the ASCII gate: grid-conformant advances but
     * proportional Latin (e.g. an ideographic font that includes proportional
     * Latin, or a plain proportional font). */
    { "proportional Latin (no ASCII mono)", { 500, 600, 700, 800, 900, 1000 }, { 160, 170, 170, 170, 170, 160 }, 6, FcFalse, FcFalse, FC_SPACING_PROPORTIONAL },
    /* Too many distinct widths to be any cell grid. */
    { "overflow",                         { 100, 200 },             { 10, 10 },                2, FcTrue,  FcFalse, FC_SPACING_PROPORTIONAL },

    /* Advances near INT_MAX, as a broken font matrix can give. */
    { "huge advances",                    { 1100000000, 2000000000 }, { 10, 10 },              2, FcFalse, FcFalse, FC_SPACING_PROPORTIONAL },
    { "huge grid advances",               { 1000000000, 2000000000, 1999999999 }, { 10, 10, 10 }, 3, FcFalse, FcTrue, FC_SPACING_MONO },
    { "huge close advances",              { 1100000000, 1110000000, 1120000000 }, { 10, 10, 10 }, 3, FcFalse, FcTrue, FC_SPACING_MONO },
};

int
main (void)
{
    size_t i;
    int    ret = 0;

    for (i = 0; i < sizeof (cases) / sizeof (cases[0]); i++) {
	const SpacingCase *c = &cases[i];
	int                total = total_of (c);
	int                got = FcSpacingClassify (c->value, c->count, c->num,
	                                             total, c->overflow,
	                                             c->ascii_monospaced);
	if (got != c->expected) {
	    fprintf (stderr, "FAIL: %-34s expected %s, got %s\n",
	             c->name, spacing_name (c->expected), spacing_name (got));
	    ret = 1;
	} else {
	    printf ("ok: %-34s %s\n", c->name, spacing_name (got));
	}
    }

    return ret;
}

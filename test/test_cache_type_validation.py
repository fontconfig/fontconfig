# Copyright (C) 2026 fontconfig Authors
# SPDX-License-Identifier: HPND

"""Regression tests for cache validation of FcValue types vs. their object.

FcCacheOffsetsValid() only looks at FcValue.type when deciding how to
validate the union payload of a value stored in a cache file, it never
cross-checks it against the FcObject of the owning FcPatternElt.

A cache file may therefore declare e.g. FC_FAMILY (declared as FcTypeString
in fcobjs.h) with a value of type FcTypeInteger and a fully attacker
controlled 64 bit union payload: the integer arm of the switch statement
accepts the qword verbatim while the string arm, which would have enforced
FcIsEncodedOffset(), is bypassed.

Consumers of a pattern dispatch on the object, not on the value type
(FcObjectValidType() is only enforced for runtime FcPatternAdd(), not for
patterns coming from a cache), so e.g. FcCompareFamilies() in fcmatch.c
calls FcValueString() on that value and dereferences the attacker
controlled qword.
"""

from fctest import FcTest
import os
import struct
import pytest


# FcType values, see fontconfig.h
FC_TYPE_VOID = 0
FC_TYPE_INTEGER = 1
FC_TYPE_DOUBLE = 2
FC_TYPE_STRING = 3
FC_TYPE_BOOL = 4
FC_TYPE_MATRIX = 5
FC_TYPE_CHARSET = 6
FC_TYPE_FT_FACE = 7
FC_TYPE_LANGSET = 8
FC_TYPE_RANGE = 9

# FcObject ids, see fcobjs.h (the order is part of the cache signature)
FC_FAMILY_OBJECT = 1
FC_WEIGHT_OBJECT = 8
FC_MATRIX_OBJECT = 32
FC_CHARSET_OBJECT = 33
FC_LANG_OBJECT = 34
FC_CUSTOM_OBJECT = 1100

# Bogus, non-canonical pointer the type confusion makes fontconfig
# dereference. Bit 0 is set, so FcIsEncodedOffset() considers it an
# offset relative to the FcValue and FcValueString() happily decodes it.
BOGUS_POINTER = 0x4141414141414141


@pytest.fixture
def fctest():
    return FcTest()


def generate_cache(
    font_dir,
    out_path,
    family_type=FC_TYPE_STRING,
    family_raw_value=None,
    family_bytes=b"TestMatchFontName\x00",
    charset_type=FC_TYPE_CHARSET,
    charset_raw_value=None,
    extra_elt=None,
):
    """Write a minimal, hand-crafted cache file for font_dir to out_path.

    The cache holds a single pattern with a FC_FAMILY and a FC_CHARSET
    element (plus an optional extra_elt tuple (object_id, vtype, raw_value)).
    The FcValue type and the raw content of the FcValue union can be
    overridden to emulate a malformed cache.
    """
    dir_bytes = font_dir.encode() + b"\x00"
    fam_bytes = family_bytes

    def align8(n):
        return (n + 7) & ~7

    def enc(off):
        return off | 1

    elts_spec = [
        (FC_FAMILY_OBJECT, "family"),
        (FC_CHARSET_OBJECT, "charset"),
    ]
    if extra_elt is not None:
        elts_spec.append((extra_elt[0], "extra"))
    elts_spec.sort(key=lambda item: item[0])
    num_elts = len(elts_spec)

    # compute layouts
    HDR_SIZE = 72
    off = HDR_SIZE
    dir_off = off;        off = align8(off + len(dir_bytes))
    fs_off = off;         off += 16
    fonts_arr_off = off;  off += 8
    pat_off = off;        off += 24
    elts_off = off;       off += num_elts * 16
    vl_offs = {}
    for _, kind in elts_spec:
        vl_offs[kind] = off
        off += 32
    fam_off = off;        off = align8(off + len(fam_bytes))
    cs_off = off;         off += 24
    leaves_off = off;     off += 8
    numbers_off = off;    off += 8
    total = off

    st = os.stat(font_dir)
    checksum = int(st.st_mtime) & 0xFFFFFFFF
    checksum_nano = st.st_mtime_ns % 1_000_000_000

    buf = bytearray(total)

    # Header
    struct.pack_into("<IiqqqiiqiiqQ", buf, 0,
        0xFC02FC04, 12, total, dir_off, fonts_arr_off, 0, 0,
        fs_off, checksum, 0, checksum_nano, (2 << 24) + (18 << 12) + 3
    )

    buf[dir_off:dir_off+len(dir_bytes)] = dir_bytes
    struct.pack_into("<iiq", buf, fs_off, 1, 1, enc(fonts_arr_off - fs_off))
    struct.pack_into("<q", buf, fonts_arr_off, enc(pat_off - fs_off))
    struct.pack_into("<iiqIi", buf, pat_off, num_elts, num_elts,
                     elts_off - pat_off, 0xFFFFFFFF, 0)

    # Value lists
    def put_vl(vl, vtype, payload=None, raw=None):
        if raw is None:
            raw = enc(payload - (vl + 8))
        struct.pack_into("<qiiQii", buf, vl, 0, vtype, 0, raw, 1, 0)

    for idx, (obj_id, kind) in enumerate(elts_spec):
        elt_pos = elts_off + idx * 16
        vl_off = vl_offs[kind]
        struct.pack_into("<iiq", buf, elt_pos, obj_id, 0, enc(vl_off - elt_pos))
        if kind == "family":
            put_vl(vl_off, family_type, payload=fam_off, raw=family_raw_value)
        elif kind == "charset":
            put_vl(vl_off, charset_type, payload=cs_off, raw=charset_raw_value)
        else:
            put_vl(vl_off, extra_elt[1], raw=extra_elt[2])

    buf[fam_off:fam_off+len(fam_bytes)] = fam_bytes

    # CharSet: FC_REF_CONSTANT, a single, empty leaf
    struct.pack_into("<iiqq", buf, cs_off, -1, 1,
                     leaves_off - cs_off, numbers_off - cs_off)
    struct.pack_into("<q", buf, leaves_off, 0x18 - leaves_off)
    struct.pack_into("<q", buf, numbers_off, 0)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(buf)

    return out_path


def generate_standalone_cache(fctest, **kwargs):
    """Craft a cache file under a name fontconfig will not regenerate."""
    # The header stores the raw mtime. Do not clamp with SOURCE_DATE_EPOCH
    fctest.env.pop('SOURCE_DATE_EPOCH', None)
    return generate_cache(
        fctest.fontdir.name,
        os.path.join(fctest.cachedir.name, "invalid_cache_file"),
        **kwargs,
    )


def test_family_declared_as_integer_is_rejected(fctest):
    """A FcTypeInteger value for the string object FC_FAMILY must be rejected.

    The union payload of such a value is never validated, but consumers of
    FC_FAMILY dereference it as a string.
    """
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest, family_type=FC_TYPE_INTEGER, family_raw_value=BOGUS_POINTER
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_charset_declared_as_integer_is_rejected(fctest):
    """A FcTypeInteger value for the charset object FC_CHARSET must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest, charset_type=FC_TYPE_INTEGER, charset_raw_value=BOGUS_POINTER
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_matrix_value_is_rejected(fctest):
    """FcTypeMatrix is never serialized into caches and must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest,
        extra_elt=(FC_MATRIX_OBJECT, FC_TYPE_MATRIX, BOGUS_POINTER),
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_ftface_value_is_rejected(fctest):
    """FcTypeFTFace is never serialized into caches and must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest,
        extra_elt=(FC_CUSTOM_OBJECT, FC_TYPE_FT_FACE, BOGUS_POINTER),
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_out_of_bounds_string_offset_is_rejected(fctest):
    """Encoded string offset pointing past cache end must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest, family_type=FC_TYPE_STRING, family_raw_value=(0x10000 | 1)
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_unterminated_string_is_rejected(fctest):
    """String extending to the end of the cache without NUL must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(fctest)
    with open(cache_path, "rb") as f:
        data = bytearray(f.read())
    # Point FC_FAMILY at the last 8 bytes of the cache, filled with non-NUL.
    data[-8:] = b"ABCDEFGH"
    # Find vl0_off: HDR(72) + align8(dir) + fs(16) + fonts(8) + pat(24) + elts(32)
    dir_len = (len(fctest.fontdir.name.encode()) + 1 + 7) & ~7
    vl0_off = 72 + dir_len + 16 + 8 + 24 + 32
    rel = (len(data) - 8) - (vl0_off + 8)
    struct.pack_into("<qiiQii", data, vl0_off, 0, FC_TYPE_STRING, 0, rel | 1, 1, 0)
    with open(cache_path, "wb") as f:
        f.write(data)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_out_of_bounds_langset_offset_is_rejected(fctest):
    """Encoded FcLangSet offset pointing past cache end must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest,
        extra_elt=(FC_LANG_OBJECT, FC_TYPE_LANGSET, 0x10000 | 1),
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_out_of_bounds_range_offset_is_rejected(fctest):
    """Encoded FcRange offset pointing past cache end must be rejected."""
    fctest.setup()
    cache_path = generate_standalone_cache(
        fctest,
        extra_elt=(FC_WEIGHT_OBJECT, FC_TYPE_RANGE, 0x10000 | 1),
    )
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache" in stderr


def test_wellformed_cache_is_accepted(fctest):
    """The generator itself must produce a cache that passes validation."""
    fctest.setup()
    cache_path = generate_standalone_cache(fctest)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 0
        assert "invalid cache" not in stderr
        assert "TestMatchFontName" in stdout

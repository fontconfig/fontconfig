# Copyright (C) 2026 fontconfig Authors
# SPDX-License-Identifier: HPND

from fctest import FcTest
import os
import struct
import pytest

@pytest.fixture
def fctest():
    return FcTest()

def generate_cache(fctest, cs_ref=-1, cs_num=1, leaves_offset_val=None, numbers_offset_val=None, leaf_val=None, invalid_cs_ptr=False):
    font_dir = fctest.fontdir.name
    out_dir = fctest.cachedir.name

    dir_bytes = font_dir.encode() + b"\x00"
    fam_bytes = b"TestMatchFontName\x00"

    def align8(n): return (n + 7) & ~7
    def enc(off): return off | 1

    # compute layouts
    HDR_SIZE = 72
    off = HDR_SIZE
    dir_off = off;        off = align8(off + len(dir_bytes))
    fs_off = off;         off += 16
    fonts_arr_off = off;  off += 8
    pat_off = off;        off += 24
    elts_off = off;       off += 2 * 16
    vl0_off = off;        off += 32
    vl2_off = off;        off += 32
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
    struct.pack_into("<iiqIi", buf, pat_off, 2, 2, elts_off - pat_off, 0xFFFFFFFF, 0)

    # Elts (FAMILY=1, CHARSET=33)
    struct.pack_into("<iiq", buf, elts_off, 1, 0, enc(vl0_off - elts_off))
    struct.pack_into("<iiq", buf, elts_off + 16, 33, 0, enc(vl2_off - (elts_off + 16)))

    # Value Lists
    def put_vl(vl, vtype, payload):
        struct.pack_into("<qiiqii", buf, vl, 0, vtype, 0, enc(payload - (vl + 8)), 1, 0)

    put_vl(vl0_off, 3, fam_off)

    if invalid_cs_ptr:
        # Point the charset pointer completely out of bounds of the cache (e.g., total + 1000)
        put_vl(vl2_off, 6, total + 1000)
    else:
        put_vl(vl2_off, 6, cs_off)

    buf[fam_off:fam_off+len(fam_bytes)] = fam_bytes

    # CharSet
    lo = leaves_offset_val if leaves_offset_val is not None else (leaves_off - cs_off)
    no = numbers_offset_val if numbers_offset_val is not None else (numbers_off - cs_off)
    struct.pack_into("<iiqq", buf, cs_off, cs_ref, cs_num, lo, no)

    lf = leaf_val if leaf_val is not None else (0x18 - leaves_off)
    struct.pack_into("<q", buf, leaves_off, lf)
    struct.pack_into("<q", buf, numbers_off, 0)

    # Save to a custom filename to prevent automatic configuration reconstruction overwrites
    out_path = os.path.join(out_dir, "invalid_cache_file")
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(buf)

    return out_path


def test_validation_non_constant_charset(fctest):
    """Verify that a charset with ref count != FC_REF_CONSTANT is rejected."""
    fctest.setup()
    # cs_ref = 0 (not constant)
    cache_path = generate_cache(fctest, cs_ref=0)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: non-constant or out-of-bounds charset" in stderr


def test_validation_out_of_bounds_charset(fctest):
    """Verify that a charset with an out-of-bounds pointer is rejected."""
    fctest.setup()
    cache_path = generate_cache(fctest, invalid_cs_ptr=True)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: non-constant or out-of-bounds charset" in stderr


def test_validation_broken_leaves_offset(fctest):
    """Verify that a charset with a broken/negative leaves offset is rejected."""
    fctest.setup()
    # cs_ref = -1, cs_num = 1, leaves_offset_val = -1 (invalid negative offset)
    cache_path = generate_cache(fctest, cs_ref=-1, leaves_offset_val=-1)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: broken charset leaves offset" in stderr


def test_validation_broken_numbers_offset(fctest):
    """Verify that a charset with a broken/negative numbers offset is rejected."""
    fctest.setup()
    # cs_ref = -1, cs_num = 1, numbers_offset_val = -1 (invalid negative offset)
    cache_path = generate_cache(fctest, cs_ref=-1, numbers_offset_val=-1)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: broken charset numbers offset" in stderr


def test_validation_broken_leaf_offset(fctest):
    """Verify that a charset with a negative leaf element offset pointing before base (out of bounds) is rejected."""
    fctest.setup()
    # cs_ref = -1, cs_num = 1, leaf_val = -1000 (points out of bounds before base)
    cache_path = generate_cache(fctest, cs_ref=-1, leaf_val=-1000)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: broken charset leaf offset" in stderr


def test_validation_valid_negative_leaf_offset(fctest):
    """Verify that a charset with a valid negative leaf offset within cache bounds is accepted."""
    fctest.setup()
    # Default leaf_val is 0x18 - leaves_off (around -250), which points to offset 24 in the header (inside cache bounds).
    # This is a valid negative leaf offset, which should be accepted and not trigger any warnings.
    cache_path = generate_cache(fctest, cs_ref=-1, cs_num=1)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 0
        assert "invalid cache" not in stderr


def test_validation_out_of_bounds_positive_leaf_offset(fctest):
    """Verify that a charset with a positive leaf offset pointing beyond the cache is rejected."""
    fctest.setup()
    # leaf_val = 1000 (points way past the end of the cache)
    cache_path = generate_cache(fctest, cs_ref=-1, cs_num=1, leaf_val=1000)
    for ret, stdout, stderr in fctest.run_cat(["-v", cache_path], debug=16):
        assert ret == 1
        assert "invalid cache: broken charset leaf offset" in stderr

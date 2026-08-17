#! /usr/bin/env python3
# Copyright (C) 2026 fontconfig Authors
# SPDX-License-Identifier: HPND

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from fctest import FcTest, FcTestFont


@pytest.fixture
def fctest():
    return FcTest()


@pytest.fixture
def fcfont():
    return FcTestFont()


@pytest.mark.parametrize("cwd", ["/", "/tmp", None])
def test_absolute_glob_is_cwd_independent(fctest, fcfont, cwd):
    """An absolute glob has to be honoured whatever the current directory is.

    FcConfigGlobAdd() used to strip a leading current directory name off
    every glob, which also fired for an absolute glob whenever the current
    directory happened to be a lexical prefix of it. Running from the root
    directory made that unconditional, since the current directory name is
    an empty string there, so every absolute glob silently lost its leading
    separator and stopped matching anything.
    """
    extraconffile = NamedTemporaryFile(
        prefix="fontconfig.", suffix=".extra.conf", mode="w", delete_on_close=False
    )
    fctest._extra.append(
        f'<include ignore_missing="yes">{fctest.convert_path(extraconffile.name)}</include>'
    )

    extraconffile.write(
        f"""
<fontconfig>
  <selectfont>
    <rejectfont>
      <glob>{fctest.convert_path(fctest.fontdir.name)}</glob>
    </rejectfont>
  </selectfont>
</fontconfig>
"""
    )
    extraconffile.close()

    fctest.setup()
    fctest.install_font(fcfont.fonts, ".")
    for ret, stdout, stderr in fctest.run_cache(
        [fctest.convert_path(fctest.fontdir.name)], cwd=cwd
    ):
        assert ret == 0, stderr
        assert "rejected" in stderr, stderr
    cache_files = [f.name for f in Path(fctest.cachedir.name).glob("*cache*")]
    assert len(cache_files) == 0

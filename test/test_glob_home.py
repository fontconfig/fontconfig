#! /usr/bin/env python3
# Copyright (C) 2026 fontconfig Authors
# SPDX-License-Identifier: HPND

import pytest
from tempfile import NamedTemporaryFile
from fctest import FcTest, FcTestFont


@pytest.fixture
def fctest():
    return FcTest()


@pytest.fixture
def fcfont():
    return FcTestFont()


def test_glob_home_unexpandable(fctest, fcfont):
    """A ~ glob must not crash when there is no home directory to expand.

    FcStrCopyFilename() returns NULL for a ~ glob when no home directory is
    available, and FcConfigGlobAdd() used to hand that NULL straight to
    strncmp().
    """
    extraconffile = NamedTemporaryFile(
        prefix="fontconfig.", suffix=".extra.conf", mode="w", delete_on_close=False
    )
    fctest._extra.append(
        f'<include ignore_missing="yes">{fctest.convert_path(extraconffile.name)}</include>'
    )

    extraconffile.write(
        """
<fontconfig>
  <selectfont>
    <rejectfont>
      <glob>~/fonts/*</glob>
    </rejectfont>
  </selectfont>
</fontconfig>
"""
    )
    extraconffile.close()

    fctest.setup()
    fctest.install_font(fcfont.fonts, ".")
    fctest.env.pop("HOME", None)
    for ret, stdout, stderr in fctest.run_cache(
        [fctest.convert_path(fctest.fontdir.name)]
    ):
        assert ret == 0, f"fc-cache did not exit cleanly: {ret}: {stderr}"

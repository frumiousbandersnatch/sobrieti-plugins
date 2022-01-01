#!/usr/bin/env pytest

import pytest
import store

def test_make():
    bs = store.Bucket()
    assert bs
    assert bs.db.execute("select * from facts").fetchall()


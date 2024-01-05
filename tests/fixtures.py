import sqlite3

import pytest


@pytest.fixture
def memsqlite(request):
    conn = sqlite3.connect(':memory:', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = conn.cursor()
    with open(request.config.rootdir / '/seed.sql') as f:
        cur.executescript(f.read())
    conn.commit()
    return conn

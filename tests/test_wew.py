import pytest

from .fixtures import memsqlite


@pytest.fixture
def websocket(mocker):
    mocker.patch('websockets.client.WebSocketClientProtocol.recv')


def test_db_connection(memsqlite):
    conn, cur = memsqlite, memsqlite.cursor()
    payload = (1, 'testworld', 1, 1)
    cur.execute(f'''INSERT INTO worlds VALUES {payload}''')
    for r in cur.execute('''SELECT * FROM worlds'''):
        assert r == payload

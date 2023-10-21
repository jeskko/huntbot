from datetime import datetime, timedelta
from unittest.mock import Mock

import nuny.config
import nuny.sheet_utils


def test_speculate_1(monkeypatch):
    nuny_conf = {
        "sonar": {
            "enable": False
        },
        "worlds": [
            {
                "initial": "x",
                "name": "xtest",
                6: {
                    "status": "XX",
                    "time": "YY"
                }
            }
        ]
    }
    monkeypatch.setattr(nuny.config, "conf", nuny_conf)

    fetch_sheet_mock = Mock()
    # First return is a number of days in a doubly-nested list
    # Second return is the status of the world according to the sheet

    # For this test, set the sheet time to 1 hour ago. Remember the units of an excel sheet are
    # the number of days since 30th Dec 1899, with the decimal part being the hours/minutes/seconds

    current_time_m1 = datetime.utcnow() - timedelta(hours=1)
    time_as_excel = (current_time_m1 - datetime(year=1899, month=12, day=30)).total_seconds() / 86400
    fetch_sheet_mock.side_effect = [[[time_as_excel]], [['Up']]]
    monkeypatch.setattr(nuny.sheet_utils, "fetch_sheet", fetch_sheet_mock)

    from nuny.misc_utils import speculate
    msg = speculate("x", "0")
    assert 'Marks are up and will start despawning' in msg

import re

import mock
import pytest
from _pytest import capture

from dsnap import prompt
from .test_aws import session, boto_conf, aws_credentials  # noqa: F401


def test_snap_id_from_input__unknown(session, capsys):
    with pytest.raises(UserWarning, match='^unknown'):
        prompt.snap_id_from_input(session, "unknown-test")

def test_snap_id_from_input__none(session):
    prompt.full_prompt = mock.MagicMock(return_value="none-test")
    assert "none-test" == prompt.snap_id_from_input(session, None)


def test_snap_id_from_input__snap(session):
    assert "snap-test" == prompt.snap_id_from_input(session, "snap-test")

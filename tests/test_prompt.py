import re

import mock
import pytest
from _pytest import capture
from moto import mock_iam, mock_ec2

from dsnap import prompt
from .test_aws import session, boto_conf, aws_credentials  # noqa: F401


def test_snap_id_from_input__unknown(session, capsys):
    with pytest.raises(UserWarning, match='^unknown'):
        prompt.snap_from_input(session, "unknown-test")

@mock_ec2
def test_snap_id_from_input__none_no_instances(session):
    with pytest.raises(UserWarning, match='no items'):
        prompt.snap_from_input(session, None)

@mock_ec2
def test_snap_id_from_input__none(session):
    resp = mock.MagicMock(return_value="none-test")
    prompt.resource_prompt = mock.MagicMock(return_value=resp)
    assert resp == prompt.snap_from_input(session, None)


def test_snap_id_from_input__snap(session):
    assert "snap-test" == prompt.snap_from_input(session, "snap-test").snapshot_id

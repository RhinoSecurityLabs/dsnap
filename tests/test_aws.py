import os

import boto3
import botocore
import pytest
from moto import mock_iam, mock_ec2


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture(scope='function')
def session(aws_credentials):
    with mock_iam():
        yield boto3.session.Session(region_name='us-east-1')


@pytest.fixture(scope='function')
def boto_conf(aws_credentials):
    with mock_iam():
        yield botocore.config.Config()

@pytest.fixture(scope='function')
def ec2(session):
    with mock_ec2():
        yield session.resource('ec2')
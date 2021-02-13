from io import BytesIO
from pathlib import Path

import pytest
from botocore.response import StreamingBody
from mypy_boto3_ebs.type_defs import BlockTypeDef

from dsnap import snapshot as s

from .test_aws import session, boto_conf, aws_credentials  # noqa: F401


@pytest.fixture(scope='function')
def local_snapshot(session, boto_conf, tmp_path: Path):
    snap = s.LocalSnapshot('./test-snapshot.img', 'test-snapshot', session, boto_conf)

    snap.path = str((tmp_path / 'test.img').absolute())

    # EBS API isn't supported by moto yet, so mock this manually
    snap.get_blocks = lambda: print('Mocked')
    snap.block_size_b = 524288
    snap.volume_size_b = s.MEGABYTE
    snap.total_blocks = 300
    return snap


def test_snapshot_id(local_snapshot: s.LocalSnapshot):
    local_snapshot.snapshot_id = 'test-snapshot'


@pytest.fixture(scope='function')
def truncate(local_snapshot: s.LocalSnapshot, tmp_path: Path):
    local_snapshot.truncate()
    return tmp_path / 'test.img'


def test_truncate(truncate: Path):
    assert truncate.stat().st_size == s.MEGABYTE
    assert truncate.read_bytes().startswith(b'\x00\x00\x00\x00\x00\x00\x00')
    assert truncate.read_bytes().endswith(b'\x00\x00\x00\x00\x00\x00\x00')


@pytest.fixture(scope='function')
def block(truncate, local_snapshot: s.LocalSnapshot):
    body = b'test1234'
    b = s.Block(local_snapshot, BlockTypeDef(
        BlockIndex=0,
        BlockToken="token",
    ))
    b.BlockData = BytesIO(body)
    b.Checksum = "k36NX7tIvUlJU2zWW401xCa4DS+DDFwwjizexCKuIkQ="
    return b


@pytest.fixture(scope='function')
def write_block(block: s.Block, local_snapshot: s.LocalSnapshot):
    written = block.write()
    assert written == 8
    return local_snapshot


def test_write_block(write_block: s.Snapshot):
    with open(write_block.path, 'rb') as f:
        assert f.read().startswith(b'test1234\x00\x00')


@pytest.fixture(scope='function')
def block_offset(truncate, local_snapshot: s.LocalSnapshot):
    body = b'test1234'
    b = s.Block(local_snapshot, BlockTypeDef(
        BlockIndex=1,
        BlockToken="token",
    ))
    b.BlockData = BytesIO(body)
    b.Checksum = "k36NX7tIvUlJU2zWW401xCa4DS+DDFwwjizexCKuIkQ="
    return b


@pytest.fixture(scope='function')
def write_block_offset(block_offset: s.Block, local_snapshot: s.LocalSnapshot):
    written = block_offset.write()
    assert written == 8
    return local_snapshot


def test_write_block_offset(write_block_offset: s.Snapshot):
    with open(write_block_offset.path, 'rb') as f:
        f.seek(524288)
        assert f.read().startswith(b'test1234\x00\x00')

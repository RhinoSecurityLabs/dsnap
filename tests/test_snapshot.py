from io import BytesIO
from pathlib import Path

import pytest
from botocore.response import StreamingBody

from dsnap import snapshot as s

from .test_aws import session, boto_conf, aws_credentials  # noqa: F401


@pytest.fixture(scope='function')
def snapshot(session, boto_conf, tmp_path: Path):
    snap = s.Snapshot('test-snapshot', session, boto_conf)

    snap.output_file = str((tmp_path / 'test.img').absolute())

    # EBS API isn't supported by moto yet, so mock this manually
    snap.get_blocks = lambda: print('Mocked')
    snap.block_size_b = 524288
    snap.volume_size_b = s.MEGABYTE
    snap.total_blocks = 300
    return snap


def test_snapshot_id(snapshot: s.Snapshot):
    snapshot.snapshot_id = 'test-snapshot'


@pytest.fixture(scope='function')
def truncate(snapshot: s.Snapshot, tmp_path: Path):
    snapshot.truncate()
    return tmp_path / 'test.img'


def test_truncate(truncate: str):
    assert truncate.stat().st_size == s.MEGABYTE
    assert truncate.read_bytes().startswith(b'\x00\x00\x00\x00\x00\x00\x00')
    assert truncate.read_bytes().endswith(b'\x00\x00\x00\x00\x00\x00\x00')


@pytest.fixture(scope='function')
def block(truncate, snapshot):
    body = b'test1234'
    return s.Block(
        BlockData=StreamingBody(BytesIO(body), len(body)),
        Offset=0,
        Checksum='k36NX7tIvUlJU2zWW401xCa4DS+DDFwwjizexCKuIkQ=',
    )


@pytest.fixture(scope='function')
def write_block(block: s.Block, snapshot: s.Snapshot):
    written = snapshot._write_block(block)
    assert written == 8
    return snapshot


def test_write_block(write_block: s.Snapshot):
    with open(write_block.output_file, 'rb') as f:
        assert f.read().startswith(b'test1234\x00\x00')


@pytest.fixture(scope='function')
def block_offset(truncate, snapshot):
    body = b'test1234'
    return s.Block(
        BlockData=StreamingBody(BytesIO(body), len(body)),
        Offset=524288,  # Equivalent to BlockIndex 1
        Checksum='k36NX7tIvUlJU2zWW401xCa4DS+DDFwwjizexCKuIkQ=',
    )


@pytest.fixture(scope='function')
def write_block_offset(block_offset: s.Block, snapshot: s.Snapshot):
    written = snapshot._write_block(block_offset)
    assert written == 8
    return snapshot


def test_write_block_offset(write_block_offset: s.Snapshot):
    with open(write_block_offset.output_file, 'rb') as f:
        f.seek(524288)
        assert f.read().startswith(b'test1234\x00\x00')

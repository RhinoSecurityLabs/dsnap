import logging
import os
import sys
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from typing import TYPE_CHECKING, List, Callable

import botocore.config
from botocore.response import StreamingBody

from dsnap.utils import sha256_check

if TYPE_CHECKING:
    from mypy_boto3_ebs.client import EBSClient
    from mypy_boto3_ebs.type_defs import BlockTypeDef

import boto3.resources

MEGABYTE: int = 1024 * 1024
GIGABYTE: int = 1024 * MEGABYTE

RUN_THREADS = 50


class Block:
    client = boto3.client

    def __init__(self, snap: 'Snapshot', resp: 'BlockTypeDef'):
        self.snapshot = snap
        self.BlockIndex = resp['BlockIndex']
        self.Offset: int = resp['BlockIndex'] * snap.block_size_b
        self.BlockToken = resp['BlockToken']
        self.BlockData: StreamingBody = None  # type: ignore[assignment]
        self.Checksum: str = ''

    def write(self) -> int:
        logging.debug(f"Writing block at offset {self.Offset}")
        data = self.BlockData.read()

        if not sha256_check(data, self.Checksum):
            raise UserWarning(f"Got block with incorrect checksum at block offset {self.Offset}")

        with os.fdopen(os.open(self.snapshot.path, os.O_RDWR | os.O_CREAT), 'rb+') as f:
            f.seek(self.Offset)
            bytes_written = f.write(data)
            f.flush()
            return bytes_written

    def fetch(self) -> 'Block':
        logging.debug(f"Getting block index {self.BlockIndex}")
        resp = self.snapshot.ebs.get_snapshot_block(
            SnapshotId=self.snapshot.snapshot_id,
            BlockIndex=self.BlockIndex,
            BlockToken=self.BlockToken,
        )
        self.BlockData = resp['BlockData']
        self.Checksum = resp['Checksum']
        return self


class Snapshot:
    def __init__(
            self,
            snapshot_id: str,
            boto3_session: boto3.session.Session = None,
            region: str = None,
            botocore_conf: botocore.config.Config = botocore.config.Config()
    ) -> None:
        # If a region is provided, override any existing session with a new one in that region.
        if region is not None:
            boto3_session = boto3.session.Session(region_name=region)
        elif boto3_session is None or not boto3_session.region_name:
            boto3_session = boto3.session.Session(region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        
        self.blocks: List[Block] = []
        self.snapshot_id = snapshot_id
        self.path = ''
        self.queue: Queue = Queue()

        ebs_config = botocore.config.Config(max_pool_connections=RUN_THREADS).merge(botocore_conf)
        self.ebs: 'EBSClient' = boto3_session.client('ebs', config=ebs_config)

        self.volume_size_b = 0
        self.total_blocks = 0
        self.blocks_written = 0
        self.block_size_b = 0

    def get_blocks(self) -> List[Block]:
        for block in self._get_blocks():
            self.blocks.append(Block(self, block))
        return self.blocks

    def _get_blocks(self) -> List['BlockTypeDef']:
        resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id)
        self.block_size_b = resp['BlockSize']
        self.volume_size_b = resp['VolumeSize'] * GIGABYTE
        logging.info(f"Volume size is {self.volume_size_b}")
        blocks = resp['Blocks']
        while resp.get('NextToken'):
            resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id, NextToken=resp.get('NextToken'))
            blocks.extend(resp['Blocks'])
        self.total_blocks = len(blocks)
        logging.info(f"Number of blocks in image: {self.total_blocks}")
        return blocks

    def run(self, func: Callable[[Block], None], threads=RUN_THREADS):
        for block in self.blocks:
            logging.debug(f"Putting block index {block.BlockIndex} on the queue")
            self.queue.put(block)
        thread_list = []
        for i in range(RUN_THREADS):
            t = Thread(target=lambda: self._run(func))
            thread_list.append(t)
            t.start()
        self.queue.join()
        for t in thread_list:
            t.join()

    def _run(self, f: Callable[[Block], None]) -> None:
        while True:
            try:
                block: Block = self.queue.get(block=False)
                f(block)
                self.blocks_written += 1
                print(f"Saved block {self.blocks_written} of {self.total_blocks}", end='\r', file=sys.stderr)
                self.queue.task_done()
            except Exception as e:
                if isinstance(e, Empty):
                    return
                else:
                    logging.exception(f"[ERROR] {e.args}")
                raise e


class LocalSnapshot(Snapshot):
    def __init__(
            self,
            dir: str,
            snapshot_id: str,
            boto3_session: boto3.session.Session = None,
            region: str = None,
            botocore_conf: botocore.config.Config = botocore.config.Config()
    ) -> None:
        super().__init__(snapshot_id, boto3_session, region, botocore_conf)
        assert dir
        self.path = str(Path(dir).joinpath(f"{snapshot_id}.img"))

    def fetch(self, force: bool = False) -> None:
        if Path(self.path).exists() and not force:
            raise FileExistsError(f"The output file '{self.path}' already exists.")
        self.path = os.path.abspath(self.path)
        print(f"Output Path: {self.path}")
        self.get_blocks()
        self.truncate()

        def download(b: Block):
            b.fetch().write()
        self.run(download)

    def truncate(self) -> None:
        with open(self.path, 'wb') as f:
            print(f"Truncating file to {self.volume_size_b/GIGABYTE} GB", file=sys.stderr)
            f.truncate(self.volume_size_b)
            f.flush()

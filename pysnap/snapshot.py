import os
from threading import Thread
from typing import TYPE_CHECKING, List, Iterator, NamedTuple, IO, Callable
import logging
from queue import Queue, Empty

import botocore
from mypy_boto3_ebs.type_defs import BlockTypeDef

if TYPE_CHECKING:
    from mypy_boto3_ebs.client import EBSClient
    from mypy_boto3_ebs.type_defs import BlockTypeDef
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.type_defs import SnapshotTypeDef

import boto3.session

MEGABYTE: int = 1024 * 1024
GIBIBYTE: int = 1024 * MEGABYTE

FETCH_THREADS=30


class WriteBlock(NamedTuple):
    File: str
    BlockData: IO[bytes]
    Offset: int


class Snapshot:
    def __init__(self, snapshot_id: str, sess: boto3.session.Session) -> None:
        self.snapshot_id = snapshot_id
        self.ebs: EBSClient = sess.client('ebs', config=botocore.config.Config(max_pool_connections=FETCH_THREADS))
        self.ec2: EC2Client = sess.client('ec2')
        self.volume_size = 0
        self.data_size_mb = 0
        self.received_mb = 0
        self.block_size_bytes = 0
        self.queue = Queue()
        self.workers = 5
        self.output_file = None

        self.get_blocks()

    def get_blocks(self) -> List[BlockTypeDef]:
        resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id)
        self.block_size_bytes = resp['BlockSize']
        self.volume_size = resp['VolumeSize'] * GIBIBYTE
        logging.info(f"Volume size is {self.volume_size}")

        self.data_size_mb += int(self.block_size_bytes * len(resp['Blocks']) / MEGABYTE)

        next_token = resp.get('NextToken')
        blocks = resp['Blocks']
        while next_token:
            resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id, NextToken=next_token)
            next_token = resp.get('NextToken')
            blocks.extend(resp['Blocks'])
            self.data_size_mb += int(resp['BlockSize'] * len(resp['Blocks']) / MEGABYTE)

        logging.info(f"Number of blocks in image: {len(blocks)}")
        return blocks

    def download(self, output_file: str):
        if not output_file:
            output_file = f"{self.snapshot_id}.img"
        self.output_file = os.path.abspath(output_file)

        with open(output_file, 'wb') as f:
            logging.info(f"Truncating file to {self.volume_size}")
            f.truncate(self.volume_size)
            f.flush()

        threads = list()
        done = False
        for i in range(FETCH_THREADS):
            t = Thread(target=self._write_blocks_worker, args=(lambda: done,))
            threads.append(t)
            t.start()

        blocks = self.get_blocks()
        for block in blocks:
            logging.debug(f"Putting block index {block['BlockIndex']} on the queue")
            self.queue.put(block)

        self.queue.join()
        done = True

        for t in threads:
            t.join()

        print(f"Output Path: {output_file}")

    def _write_blocks_worker(self, done: Callable):
        while not self.queue.empty() or not done():
            try:
                block: BlockTypeDef = self.queue.get(timeout=1)
                write_block: WriteBlock = self.fetch_block(block)
                self.received_mb += self.write_block(write_block) / MEGABYTE
                print(f"Received {self.received_mb} of {self.data_size_mb}", end='\r')
                self.queue.task_done()
            except Exception as e:
                if isinstance(e, Empty):
                    continue
                else:
                    logging.exception(f"[ERROR] {e.args}")
                    raise e

    def fetch_block(self, block: BlockTypeDef) -> WriteBlock:
        logging.debug(f"Getting block index {block['BlockIndex']}")
        resp = self.ebs.get_snapshot_block(
            SnapshotId=self.snapshot_id,
            BlockIndex=block['BlockIndex'],
            BlockToken=block['BlockToken'],
        )

        # BlockIndex is equal to 512 KiB and seek uses bytes.
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ebs.html#EBS.Client.put_snapshot_block
        return WriteBlock(
            File=self.output_file,
            Offset=block['BlockIndex'] * self.block_size_bytes,
            BlockData=resp['BlockData'],
        )

    @staticmethod
    def write_block(block: WriteBlock):
        logging.debug(f"Writing block at offset {block.Offset}")
        """Takes a WriteBlock object to write to disk and yields the number of MiB's for each write."""
        with os.fdopen(os.open(block.File, os.O_RDWR | os.O_CREAT), 'rb+') as f:
            f.seek(block.Offset)
            bytes_written = f.write(block.BlockData.read())
            f.flush()
            return bytes_written


def describe_snapshots(sess, **kwargs) -> Iterator['SnapshotTypeDef']:
    ec2: EC2Client = sess.client('ec2')
    for page in ec2.get_paginator('describe_snapshots').paginate(**kwargs):
        for snapshot in page['Snapshots']:
            yield snapshot

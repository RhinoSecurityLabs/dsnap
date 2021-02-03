import os
from typing import TYPE_CHECKING, List, Iterator

if TYPE_CHECKING:
    from mypy_boto3_ebs.client import EBSClient
    from mypy_boto3_ebs.type_defs import BlockTypeDef
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.type_defs import SnapshotTypeDef

import boto3.session

GIBIBYTE: int = 1024 * 1024 * 1024


class WriteBlock(NamedTuple):
    File: BinaryIO
    BlockIndex: int
    BlockData: IO[bytes]


class Snapshot:
    def __init__(self, snapshot_id: str, sess: boto3.session.Session) -> None:
        self.snapshot_id = snapshot_id
        self.blocks: List[BlockTypeDef] = []
        self.ebs: EBSClient = sess.client('ebs')
        self.ec2: EC2Client = sess.client('ec2')
        self.received_mb = 0
        self.volume_size = 0
        self.data_size_mb = 0
        self.queue = Queue()

        self.get_blocks()

    def get_blocks(self):
        resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id)
        next_token = resp.get('NextToken')
        self.volume_size = resp['VolumeSize'] * GIBIBYTE
        logging.info(f"Volume size is {self.volume_size}")
        self.blocks = resp['Blocks']
        self.data_size_mb += int(resp['BlockSize'] * len(resp['Blocks']) / 1024 / 1024)

        while next_token:
            resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id, NextToken=next_token)
            next_token = resp.get('NextToken')
            self.blocks.extend(resp['Blocks'])
            self.data_size_mb += int(resp['BlockSize'] * len(resp['Blocks']) / 1024 / 1024)
        return self.blocks

    def download(self, output_file: str):
        if not output_file:
            output_file = f"{self.snapshot_id}.img"
        output_file = os.path.abspath(output_file)

        with open(output_file, 'wb') as f:
            logging.info(f"Truncating file to {self.volume_size}")
            f.truncate(self.volume_size)
            f.flush()
            for block in self.get_blocks(): # TODO set volume size first
                resp = self.ebs.get_snapshot_block(
                    SnapshotId=self.snapshot_id,
                    BlockIndex=block['BlockIndex'],
                    BlockToken=block['BlockToken'],
                )
                self.queue.put(WriteBlock(File=f, **resp))

        print(f"Output Path: {output_file}")

    def _write_block(self, block: WriteBlock):
        block.File.seek(block.BlockIndex)
        self.received_mb += block.File.write(block.BlockData.read())
        print(f"Downloaded {self.received_mb / 1024 / 1024} of {self.data_size_mb}", end='\r')

    def _write_blocks_worker(self):
        while True:
            try:
                block = self.queue.get()
                self.write_block(block)
                self.queue.task_done()
            except Exception as e:
                logging.exception("[ERROR]")



def describe_snapshots(sess, **kwargs) -> Iterator['SnapshotTypeDef']:
    ec2: EC2Client = sess.client('ec2')
    for page in ec2.get_paginator('describe_snapshots').paginate(**kwargs):
        for snapshot in page['Snapshots']:
            yield snapshot

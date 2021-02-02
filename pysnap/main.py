import os

import typer
import boto3
import boto3.session
import typing
from typing import List

import json
from enum import Enum

from mypy_boto3_ec2.type_defs import SnapshotTypeDef

if typing.TYPE_CHECKING:
    from mypy_boto3_ebs.client import EBSClient
    from mypy_boto3_ebs.type_defs import BlockTypeDef
    from mypy_boto3_ec2.client import EC2Client

app = typer.Typer()
sess: boto3.session.Session = None


class Snapshot:
    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id
        self.blocks: List[BlockTypeDef] = []
        self.ebs: EBSClient = sess.client('ebs')
        self.ec2: EC2Client = sess.client('ec2')
        self.received_mb = 0
        self.size_mb = 0

    def get_blocks(self):
        resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id)
        next_token = resp.get('NextToken')
        self.blocks = resp['Blocks']
        self.size_mb += int(resp['BlockSize'] * len(resp['Blocks'])/1024/1024)

        while next_token:
            resp = self.ebs.list_snapshot_blocks(SnapshotId=self.snapshot_id, NextToken=next_token)
            next_token = resp.get('NextToken')
            self.blocks.extend(resp['Blocks'])
            self.size_mb += int(resp['BlockSize'] * len(resp['Blocks'])/1024/1024)
        return self.blocks

    def download(self, output_file: str):
        if not output_file:
            output_file = f"{self.snapshot_id}.img"
        output_file = os.path.abspath(output_file)

        with open(output_file, 'wb') as f:
            for block in self.get_blocks():
                resp = self.ebs.get_snapshot_block(
                    SnapshotId=self.snapshot_id,
                    BlockIndex=block['BlockIndex'],
                    BlockToken=block['BlockToken'],
                )
                self.received_mb += f.write(resp['BlockData'].read())
                print(f"Downloaded {self.received_mb/1024/1024} of {self.size_mb}", end='\r')

        print(f"IMG location: {output_file}")


@app.callback()
def session(region: str = typer.Option(default='us-east-1'), profile: str = typer.Option(default=None)):
    global sess
    sess = boto3.session.Session(region_name=region, profile_name=profile)


class Output(str, Enum):
    list = "list"
    json = "json"


@app.command("list")
def list_snapshots(format: Output = Output.list):
    print("           {}          |   {}   |   {}".format('Id', 'Owner ID', 'State'))

    for snapshot in describe_snapshots(OwnerIds=['self']):
        if format == format.list:
            print("{}   {}   {}".format(snapshot['SnapshotId'], snapshot['OwnerId'], snapshot['State']))
        elif format == format.json:
            print(json.dumps(snapshot, default=str))


def describe_snapshots(**kwargs) -> typing.Iterator[SnapshotTypeDef]:
    ec2: EC2Client = sess.client('ec2')
    for page in ec2.get_paginator('describe_snapshots').paginate(**kwargs):
        for snapshot in page['Snapshots']:
            yield snapshot


@app.command()
def download(snapshot_id: str):
    snap = Snapshot(snapshot_id)
    snap.download("output.img")

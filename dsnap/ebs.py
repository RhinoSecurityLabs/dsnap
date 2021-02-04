from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, List, Dict

import boto3.session
import botocore.config
import sys

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.type_defs import SnapshotTypeDef



class Ebs:
    def __init__(
            self,
            boto3_session: boto3.session.Session = boto3.session.Session(),
            botocore_conf: Optional[botocore.config.Config] = botocore.config.Config(region_name='us-east-1')
    ) -> None:
        self.boto3_session = boto3_session
        self.botocore_conf = botocore_conf
        self.snapshots: OrderedDict[str, 'SnapshotTypeDef'] = OrderedDict({})

    def set_snapshots(self, snapshots: List[dict]) -> None:
        self.snapshots = dict(map(lambda s: (s['SnapshotId'], s), snapshots))


    def get_snapshots(self, **kwargs) -> Dict[str, 'SnapshotTypeDef']:
        """Gets available snapshots with the current class config. Keyword args are passed through to describe_snapshots.

        This method returns a list of snapshot dictionaries as well as appends any newly found snapshot to self.snapshots which
        is used for snapshot_prompt. This needs to be run before snapshot_prompt if you want to be prompted for currently
        available snapshots.
        """
        ec2: EC2Client = self.boto3_session.client('ec2', config=self.botocore_conf)
        for page in ec2.get_paginator('describe_snapshots').paginate(**kwargs):
            for snap in page['Snapshots']:
                self.snapshots[snap['SnapshotId']] = snap
        return self.snapshots

    def snapshot_prompt(self) -> 'SnapshotTypeDef':
        """Prompt's the user for a snapshot to select from the items set in self.snapshots and returns a SnapshotTypeDef dict.

        You can either set self.snapshots your self to avoid API call's or call self.get_snapshots prior to this call to get
        snapshots for the currently configured region.
        """
        for i, snap in enumerate(self.snapshots.values()):
            print(f"{i}) {snap['SnapshotId']} (Description: {snap['Description']}, Size: {snap['VolumeSize']}GB)")
        answer = int(input("Select snapshot: "))
        try:
            return list(self.snapshots.values())[answer]
        except IndexError:
            print(f"Invalid selection, valid inputs are 0 through {len(self.snapshots) - 1}", file=sys.stderr)
            return self.snapshot_prompt()

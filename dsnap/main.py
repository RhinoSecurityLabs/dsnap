import os
import sys
from enum import Enum
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import boto3
import boto3.session
from typer import Argument, Option, Typer

from dsnap.snapshot import Snapshot
from dsnap.utils import item_prompt, create_tmp_snap, ask_to_run

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r

app = Typer()

sess: boto3.session.Session = boto3.session.Session()


class Output(str, Enum):
    list = "list"
    json = "json"


@app.callback()
def session(region: str = Option(default='us-east-1'), profile: str = Option(default=None)):
    global sess
    sess = boto3.session.Session(region_name=region, profile_name=profile)


@app.command("list")
def list_snapshots(format: Output = Output.list):
    EC2(boto3_session=sess).list_snapshots(format, OwnerIds=['self'])


# Called if no snapshot_id is specified when running get
def instance_prompt(value: Optional[str]) -> str:
    if value:
        return value
    else:
        ec2 = sess.resource('ec2')
        instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        inst: 'r.Instance' = item_prompt(instances, jmespath_msg='[PrivateDnsName, VpcId, SubnetId]')
        snap = volume_prompt(inst)
        return snap and snap.snapshot_id


def snapshot_prompt(vol: 'r.Volume') -> 'r.Snapshot':
    snap: 'r.Snapshot'
    snaps = list(vol.snapshots.all())
    if len(snaps) == 0:
        snap = ask_to_run("No snapshots found, create one?", lambda: create_tmp_snap(vol))
    elif len(snaps) == 1:
        snap = snaps[0]
    else:
        snap = item_prompt(snaps, jmespath_msg='[StartTime, OwnerId, Description]')
    return snap


def volume_prompt(inst) -> 'r.Snapshot':
    vols: List['r.Volume'] = list(inst.volumes.all())
    vol = vols[0] if len(vols) == 1 else item_prompt(vols, jmespath_msg='Attachments[*].Device')
    return snapshot_prompt(vol)


@app.command()
def get(id: str = Argument(default=None, callback=instance_prompt), output: Path = Option(Path("output.img"))):
    if not id:
        # id is None when user doesn't complete the instance_prompt
        print("Exiting...")
        sys.exit()
    elif id.startswith('snap-'):
        snap = Snapshot(id, sess)
    elif id.startswith('i-'):
        ec2: r.EC2ServiceResource = sess.resource('ec2')
        vol: r.Volume = volume_prompt(ec2.Instance(id))
        snap = Snapshot(vol.snapshot_id, boto3_session=sess)
    else:
        # Otherwise something was specified but we don't know what
        print("Unknown argument type, first argument should be an Instance Id or Snapshot Id")

    snap.download(output.absolute().as_posix())

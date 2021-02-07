import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import boto3
from typer import Argument, Option, Typer

from dsnap import utils
from dsnap.snapshot import Snapshot
from dsnap.utils import ask_to_create_snapshot

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r

app = Typer()

sess: boto3.session.Session = boto3.session.Session()

# This gets set via @app.callback before any command runs.
ec2: 'r.EC2ServiceResource' = None  # type: ignore[assignment]


@app.callback()
def session(region: str = Option(default='us-east-1'), profile: str = Option(default=None)):
    global sess, ec2
    sess = boto3.session.Session(region_name=region, profile_name=profile)
    ec2 = sess.resource('ec2')


@app.command("list")
def list_snapshots():
    print("           Id          |   Owneer ID   | Description")
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    for snap in ec2.snapshots.filter(OwnerIds=['self']).all():
        print(f"{snap.id}   {snap.owner_id}   {snap.description}")


def instance_prompt(value: str):
    if value:
        return value
    else:
        try:
            assert ec2
            inst = utils.instance_prompt(ec2.instances.filter(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            ))
            vol = utils.volume_prompt(inst.volumes)
            snap = utils.snapshot_prompt(vol.snapshots) or ask_to_create_snapshot(vol)
            return snap and snap.snapshot_id
        except UserWarning as e:
            print(*e.args)
            sys.exit(1)


@app.command()
def get(id: str = Argument(default=None, callback=instance_prompt), output: Optional[Path] = None):
    if id.startswith('snap-'):
        snap_id = id
    elif id.startswith('i-'):
        vol = utils.volume_prompt(ec2.Instance(id).volumes)
        snap_id = (utils.snapshot_prompt(vol.snapshots) or ask_to_create_snapshot(vol)).snapshot_id
    else:
        if not id:    # id is None when user doesn't complete the instance_prompt
            print("Exiting...")
        else:         # Otherwise something was specified but we don't know what
            print("Unknown argument type, first argument should be an Instance Id or Snapshot Id")
        sys.exit(1)

    try:
        snap = Snapshot(snap_id, boto3_session=sess)
        path = output and output.absolute().as_posix()
        snap.download(path or f"{id}.img")
    except UserWarning as e:
        print(*e.args)
        sys.exit(2)
    except Exception as e:
        resp = getattr(e, 'response', None)
        if resp and resp['Error']['Message']:
            print(resp['Error']['Message'])
            sys.exit(1)
        else:
            raise e

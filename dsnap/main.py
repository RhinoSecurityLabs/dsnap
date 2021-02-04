import json
from enum import Enum
from pathlib import Path
from typing import Optional, Iterator, TYPE_CHECKING

import boto3
import boto3.session
from typer import Argument, Option, Typer

from dsnap.ebs import Ebs
from dsnap.snapshot import Snapshot

if TYPE_CHECKING:
    from mypy_boto3_ec2.type_defs import SnapshotTypeDef

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
    print("           {}          |   {}   | {}".format('Id', 'Owner ID', 'Description'))
    ebs = Ebs(boto3_session=sess)
    for (id, snapshot) in ebs.get_snapshots(OwnerIds=['self']).items():
        if format == format.list:
            print("{}   {}   {}".format(id, snapshot['OwnerId'], snapshot['Description']))
        elif format == format.json:
            print(json.dumps(snapshot, default=str))


# Called if no snapshot_id is specified when running get
def snapshot_prompt(value: Optional[str]) -> str:
    if value:
        return value
    else:
        ebs = Ebs(boto3_session=sess)
        ebs.get_snapshots(OwnerIds=['self'])
        snapshot: 'SnapshotTypeDef' = ebs.snapshot_prompt()
        return snapshot['SnapshotId']

@app.command()
def get(snapshot_id: str = Argument(default=None, callback=snapshot_prompt), output: Path = Option(Path("output.img"))):
    snap = Snapshot(snapshot_id, sess)
    snap.download(output.absolute().as_posix())

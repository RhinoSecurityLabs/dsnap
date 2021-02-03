import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import boto3
import boto3.session
import typer

from dsnap.snapshot import Snapshot, describe_snapshots

app = typer.Typer()

sess: boto3.session.Session = None


class Output(str, Enum):
    list = "list"
    json = "json"


@app.callback()
def session(region: str = typer.Option(default='us-east-1'), profile: str = typer.Option(default=None)):
    global sess
    sess = boto3.session.Session(region_name=region, profile_name=profile)


@app.command("list")
def list_snapshots(format: Output = Output.list):
    print("           {}          |   {}   |   {}".format('Id', 'Owner ID', 'State'))
    for snapshot in describe_snapshots(sess, OwnerIds=['self']):
        if format == format.list:
            print("{}   {}   {}".format(snapshot['SnapshotId'], snapshot['OwnerId'], snapshot['State']))
        elif format == format.json:
            print(json.dumps(snapshot, default=str))


# Called if no snapshot_id is specified when running get
def snapshot_prompt(value: Optional[str]) -> str:
    if value:
        return value
    else:
        snapshots = [x for x in describe_snapshots(sess, OwnerIds=['self'])]
        for i, k in enumerate(snapshots):
            print(f"{i}) {k['SnapshotId']} (Description: {k['Description']}, Size: {k['VolumeSize']}GB)")
        answer = typer.prompt("Select snapshot")
        try:
            return snapshots[int(answer)]['SnapshotId']
        except IndexError:
            print(f"Invalid selection, valid inputs are 0 through {len(snapshots)-1}", file=sys.stderr)
            return snapshot_prompt(None)


@app.command()
def get(snapshot_id: str = typer.Argument(default=None, callback=snapshot_prompt), output: Path = typer.Option(Path("output.img"))):
    snap = Snapshot(snapshot_id, sess)
    snap.download(output.absolute().as_posix())

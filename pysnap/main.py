import json
from enum import Enum
from pathlib import Path

import boto3
import boto3.session
import typer

from pysnap.snapshot import Snapshot, describe_snapshots

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


@app.command()
def download(snapshot_id: str, output: Path = typer.Option(Path("output.img"))):
    snap = Snapshot(snapshot_id, sess)
    snap.download(output.absolute())

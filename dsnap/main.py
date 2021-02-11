import logging

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import boto3
from typer import Argument, Option, Typer

from dsnap import utils
from dsnap.snapshot import Snapshot
from dsnap.prompt import snap_id_from_input

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r

app = Typer()

sess: boto3.session.Session = boto3.session.Session()

# This gets set via @app.callback before any command runs.
ec2: 'r.EC2ServiceResource' = None  # type: ignore[assignment]


@app.callback()
def session(region: str = Option(default='us-east-1'), profile: str = Option(default=None)):
    """This is function set's up various global settings.

    It is called by Typer before any of the other commands run due to the @app.callback decorator.
    """
    global sess, ec2
    sess = boto3.session.Session(region_name=region, profile_name=profile)
    ec2 = sess.resource('ec2')


@app.command()
def init(out_dir: Path = Path('.'), force: bool = False):
    output = utils.init_vagrant(out_dir, force)
    if output:
        print(f"Wrote Vagrantfile to {output}")
    else:
        print(f"Vagrantfile already exists at {output}, use the --force to overwrite.")


@app.command("list")
def list_snapshots():
    print("           Id          |   Owneer ID   | Description")
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    for snap in ec2.snapshots.filter(OwnerIds=['self']).all():
        print(f"{snap.id}   {snap.owner_id}   {snap.description}")


@app.command()
def get(id: str = Argument(None), output: Optional[Path] = None):
    # snap_id will be None in cases of invalid argument or no snapshot was selected
    try:
        snap_id = snap_id_from_input(sess, id)
    except UserWarning as e:
        print(*e.args, '\nExiting...')
        sys.exit(1)

    try:
        logging.info(f"Selected snapshot with id {snap_id}")
        snap = Snapshot(snap_id, boto3_session=sess)
        path = output and output.absolute().as_posix()
        snap.download(path or f"{snap.snapshot_id}.img")
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

from pathlib import Path
from typing import TYPE_CHECKING, Optional, List

import boto3
import typer
from typer import Option, Typer

from dsnap import utils
from dsnap.prompt import snap_from_input, download_snap_id, snaps_from_input, take_snapshot, vol_from_id
from dsnap.utils import fatal

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r

app = Typer(name="dsnap", help="Utility for downloading EBS snapshots using the EBS Direct API's.")

sess: boto3.session.Session = boto3.session.Session()

# This gets set via @app.callback before any command runs.
ec2: 'r.EC2ServiceResource' = None  # type: ignore[assignment]


@app.callback()
def session(
        region: str = Option(default='us-east-1', help="Sets the AWS region.", metavar="REGION"),
        profile: str = Option(default=None, help="Shared credential profile to use.", metavar="PROFILE")
):
    global sess, ec2
    sess = boto3.session.Session(region_name=region, profile_name=profile)
    ec2 = sess.resource('ec2')


@app.command()
def init(
        out_dir: Path = typer.Option(Path('.'), help='Output directory to write Vagrantfile'),
        force: bool = typer.Option(False, help='Overwrite any existing Vagrantfile.')
):
    """
    Write out a Vagrantfile template to explore downloaded snapshots.

    If --out-dir is used the given directory will be used instead.
    If --force is used we will overwrite an already present Vagrantfile

    To use the outputed Vagrantfile set the IMAGE environment to the path of the snapshot you want to mount and run vagrant
    up. For example:

    % dsnap init
    % IMAGE=snap-0543a8681adce0086.img vagrant up
    % vagrant ssh
    """
    output = utils.init_vagrant(out_dir, force)
    if output:
        print(f"Wrote Vagrantfile to {typer.style('./'+str(output), bold=True)}")
    else:
        print(f"Vagrantfile already exists at {output}, use the --force to overwrite.")


@app.command("list")
def list_snapshots(
        instance_id: str = typer.Argument(None, help='Optional instance ID to limit listed snapshots to.'),
        devices: List[str] = typer.Option(['/dev/sda', '/dev/xvda'], help='Optional device name to limit snapshots to.'),
):
    """
    List snapshots in AWS.

    If --instance-id is used then snapshots will be limited to that instances default device attachments.
    If --devices is used alongside --instance-id then listed snapshots are for that instances given devices, by default this
    is /dev/sda and /dev/xvda.
    """
    print(typer.style("           Id          |   Owneer ID   | Description   ", underline=True))
    try:
        for snap in snaps_from_input(sess, instance_id, devices):
            print(f"{typer.style(snap.id, bold=True)}   {snap.owner_id}   {snap.description}")
    except UserWarning as e:
        fatal(*e.args)


@app.command()
def get(
        # We use the filename to determine the snapshot id so we can only use directories for the output option.
        output: Path = typer.Option(
            Path('.'),
            file_okay=False,
            dir_okay=True,
            help='If specified output the snapshot to the given directory, the name however is always the snapshot id.',
        ),
        force: bool = typer.Option(False, help='If specified and the snapshot already exists then overwrite it.'),
        ids: Optional[List[str]] = typer.Argument(default=None, help='The remote snapshot ID to fetch.')
):
    """
    Download a snapshot for a given instance or snapshot ID.

    If no Argument is passed then you'll be prompted to select an instance, volume and snapshot to download. If no snapshot
    exists, you can optionally create a temporary one.

    If an instance ID is passed a snapshot for that instance will be downloaded, if more then one exists you'll be prompted
    to select a one.

    If a snapshot ID is passed that snapshot will be downloaded and you will not be prompted for any additional info.
    """
    try:
        if not ids:
            snap = snap_from_input(sess, ids)
            download_snap_id(sess, force, output, snap.id)
        else:
            for id in ids:
                snap = snap_from_input(sess, id)
                download_snap_id(sess, force, output, snap.id)
    except (UserWarning, FileExistsError) as e:
        fatal(*e.args)


@app.command()
def create(ids: List[str] = typer.Argument(
    None,
    help='One or more ID\'s of a instance or volume to create a snapshot for. To avoid being prompted use an explict volume ID'
         ' rather then an instance ID.'
)):
    """
    Create a snapshot for the given instances default device volume.

    The passed argument should be an instance ID, where a snapshot will be created from the default device volume, either
    /dev/sda or /dev/xvda.
    """
    try:
        if not ids:
            fatal("must pass at least one instance or volume id as an argument")
        for i in ids:
            vol = vol_from_id(sess, i)
            s = take_snapshot(vol)
            print(f"Created snapshot {typer.style(s.id, bold=True)} from instance " f"{typer.style(i, bold=True)}")

    except UserWarning as e:
        fatal(*e.args)


@app.command()
def delete(ids: List[str] = typer.Argument(None, help='One or more ID\'s of snapshots to delete')):
    """
    Delete a given snapshot.

    The passed argument should be a snapshot ID to delete.
    """
    if not ids:
        fatal("must pass at least one instance id as an argument")
    for i in ids:
        try:
            s = ec2.Snapshot(i)
            s.delete()
            print(f"Deleted snapshot {typer.style(s.id, bold=True)}")
        except UserWarning as e:
            fatal(*e.args)

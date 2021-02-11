import json
import sys
from typing import Optional, cast, List, TYPE_CHECKING

import boto3
import jmespath
from boto3.resources.base import ServiceResource
from boto3.resources.collection import ResourceCollection

from dsnap.utils import get_name_tag, create_tmp_snap

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r


def snap_id_from_input(sess, id) -> str:
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    if not id:
        snap_id = full_prompt(sess)
    elif id.startswith('snap-'):
        snap_id = id
    elif id.startswith('i-'):
        vol = volume_prompt(ec2.Instance(id).volumes)
        snap_id = (snapshot_prompt(vol.snapshots) or ask_to_create_snapshot(vol)).snapshot_id
    else:
        raise UserWarning("unknown argument type, first argument should be an Instance Id or Snapshot Id")
    return snap_id


def full_prompt(sess: boto3.Session) -> str:
    """Prompts the user for all information.

    This is run when dsnap get is run without any options. First we prompt for the EC2
    instance to run against, prompt again if there's if the instance has multiple
    volumes, prompt again for snapshot if volume has multiple snapshots.
    """
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    inst = instance_prompt(ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    ))
    vol = volume_prompt(inst.volumes)
    snap = snapshot_prompt(vol.snapshots) or ask_to_create_snapshot(vol)
    return snap.snapshot_id


def item_prompt(collection: ResourceCollection, jmespath_msg: str = None) -> ServiceResource:
    """Prompt's the user for an item to select from the items passed. Item is expected to support the Item protocol."""
    items = list(collection.all())
    if len(items) == 0:
        raise UserWarning(f'No items found when calling {collection._py_operation_name}')

    msg = ''
    for i, item in enumerate(items):
        if jmespath_msg:
            # dump and load json to convert datetime and similar to something readable
            data = json.loads(json.dumps(item.meta.data, default=str))
            msg = ', '.join(jmespath.search(jmespath_msg, data=data))
        name = get_name_tag(item.tags)
        print(f"{i}) {item.id} {name and f'Name: {name}, '}({msg})")

    answer = int(input(f'Select {list(items)[0].meta.resource_model.name}: '))

    try:
        return list(items)[answer]
    except IndexError:
        print(f"Invalid selection, valid inputs are 0 through {len(items) - 1}", file=sys.stderr)
        return item_prompt(collection)


# Called if no snapshot_id is specified when running get
def instance_prompt(instances: ResourceCollection) -> 'r.Instance':
    """Prompts the user to select an EC2 Instance of passed in instances"""
    return cast('r.Instance', item_prompt(instances, jmespath_msg='[PrivateDnsName, VpcId, SubnetId]'))


def snapshot_prompt(snapshots: ResourceCollection) -> Optional['r.Snapshot']:
    """Prompts the user to select a EC2 Snapshot of passed in snapshots"""
    snaps = list(snapshots.all())
    if len(snaps) == 0:
        return None
    elif len(snaps) == 1:
        snap = snaps[0]
    else:
        snap = cast('r.Snapshot', item_prompt(snapshots, jmespath_msg='[StartTime, OwnerId, Description]'))
    return snap


def volume_prompt(volumes: ResourceCollection) -> 'r.Volume':
    """Prompts the user to select a Volume of passed in volumes"""
    vols: List['r.Volume'] = list(volumes.all())
    return vols[0] if len(vols) == 1 else cast('r.Volume', item_prompt(volumes, jmespath_msg='Attachments[*].Device'))


def ask_to_run(msg, func):
    resp = input(f'{msg} [y/N]: ')
    if resp.lower() == 'y':
        return func()
    return None


def ask_to_create_snapshot(vol: 'r.Volume') -> 'r.Snapshot':
    """Asks the user if we should to create a temporary snapshot.

    If the answer is Y we start snapshot creation, wait for it to finish and register a function to
    delete the snapshot on exit.
    """
    return ask_to_run("No snapshots found, create one?", lambda: create_tmp_snap(vol))

import json
import sys
from typing import Optional, cast, TYPE_CHECKING, TypeVar, Iterable

import jmespath
from boto3.resources.collection import ResourceCollection

from dsnap.snapshot import LocalSnapshot
from dsnap.utils import get_name_tag, create_tmp_snap, fatal

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r


def snaps_from_input(sess, id, devices):
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    if not id:
        for snap in ec2.snapshots.filter(OwnerIds=['self']).all():
            yield snap
    elif id.startswith("i-"):
        i: 'r.Instance' = ec2.Instance(id)
        for d in i.block_device_mappings:
            vol = ec2.Volume(d['Ebs']['VolumeId'])
            for snap in vol.snapshots.all():
                yield snap
    else:
        raise UserWarning(f"Unexpected argument format: {id}, use an instance id or omit the argument to list all snapshots")


def snap_from_input(sess, id) -> 'r.Snapshot':
    """download_from_id is meant to be called from the cli commands and will exit in the case of an error"""
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    vol: Optional['r.Volume'] = None

    if not id:
        inst: 'r.Instance' = resource_prompt(ec2.instances.all(), '[PrivateDnsName, VpcId, SubnetId]')
        vol = resource_prompt(inst.volumes.all(), 'Attachments[*].Device')
        try:
            snap = resource_prompt(cast('r.Volume', vol).snapshots.all(), '[StartTime, OwnerId, Description]')
        except UserWarning:
            snap = ask_to_create_snapshot(vol)
    elif id.startswith('snap-'):
        snap = ec2.Snapshot(id)
    elif id.startswith('i-'):
        vol = resource_prompt(ec2.Instance(id).volumes.all(), 'Attachments[*].Device')
        try:
            snap = resource_prompt(cast('r.Volume', vol).snapshots.all(), '[StartTime, OwnerId, Description]')
        except UserWarning:
            snap = ask_to_create_snapshot(vol)
    else:
        raise UserWarning('unknown argument type, first argument should be an Instance Id or Snapshot Id')

    if not snap:
        raise UserWarning("no snapshot selected")

    return snap


def vol_from_id(sess, i: str) -> 'r.Volume':
    """download_from_id is meant to be called from the cli commands and will exit in the case of an error"""
    ec2: 'r.EC2ServiceResource' = sess.resource('ec2')
    if not i:
        inst: 'r.Instance' = resource_prompt(ec2.instances.all(), '[PrivateDnsName, VpcId, SubnetId]')
        vol: 'r.Volume' = resource_prompt(inst.volumes.all(), 'Attachments[*].Device')
    elif i.startswith('vol-'):
        vol = ec2.Volume(i)
    elif i.startswith('i-'):
        vol = resource_prompt(ec2.Instance(i).volumes.all(), 'Attachments[*].Device')
    else:
        raise UserWarning("unknown argument type, first argument should be an Instance Id or Snapshot Id")

    # vol will be None in cases of invalid argument or no snapshot was selected
    if not vol:
        fatal('Exiting...')

    return vol


def download_snap_id(sess, force, output, snap_id):
    """download_from_id is meant to be called from the cli commands and will exit in the case of an error"""
    print(f"Selected snapshot with id {snap_id}")
    path = (output and output.absolute().as_posix()) or f"{snap_id}.img"
    LocalSnapshot(path, snap_id, boto3_session=sess).fetch(force=force)


T = TypeVar('T')


def item_prompt(resources: Iterable[T], jmespath_msg: str = None) -> T:
    """Prompt's the user for an item to select from the items passed. Item is expected to support the Item protocol."""
    resources = cast(ResourceCollection, resources)

    items = list(resources.all())
    if not resources or len(items) == 0:
        raise UserWarning(f'no items found when calling {resources._py_operation_name}')
    elif len(items) == 1:
        # No need to make a selection if there's only one option
        return list(items)[0]

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
        return item_prompt(resources)


def resource_prompt(resource: 'Iterable[T]', jmespath_msg='') -> T:
    resource = cast('ResourceCollection', resource)
    return item_prompt(resource, jmespath_msg=jmespath_msg)


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


def take_snapshot(vol: 'r.Volume') -> 'r.Snapshot':
    # volumes can be attached to more then one instance at a time so include all attachments in the description
    devices = ', '.join([a['Device'] for a in vol.attachments])
    instances = ', '.join([a['InstanceId'] for a in vol.attachments])
    desc = f"Instance(s): {instances}, Volume: {vol.id}, Device: {devices}"
    print(f"Creating snapshot for {desc}")

    snap = vol.create_snapshot(
        Description=f'dsnap ({desc})',
        TagSpecifications=[{
            'ResourceType': 'snapshot',
            'Tags': [{'Key': 'dsnap', 'Value': 'true'}]
        }]
    )
    snap.wait_until_completed()
    return snap

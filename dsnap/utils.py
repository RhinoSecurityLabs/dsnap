import atexit
import hashlib
import json
import logging
import signal
from base64 import b64encode

import sys
from typing import List, Iterable, Dict, cast, Optional
import jmespath

from typing_extensions import TYPE_CHECKING

from boto3.resources.base import ServiceResource
from boto3.resources.collection import ResourceCollection

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r


def get_tag(tags: Iterable[Dict[str, str]], key: str) -> str:
    if not tags:
        return ''
    name_tag = filter(lambda t: t['Key'] == 'Name', tags)
    return next(map(lambda t: t['Value'], name_tag), default='')


def get_name_tag(tags: List[dict]) -> str:
    return get_tag(tags, 'Name')


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
    return cast('r.Instance', item_prompt(instances, jmespath_msg='[PrivateDnsName, VpcId, SubnetId]'))


def snapshot_prompt(snapshots: ResourceCollection) -> Optional['r.Snapshot']:
    snaps = list(snapshots.all())
    if len(snaps) == 0:
        return None
    elif len(snaps) == 1:
        snap = snaps[0]
    else:
        snap = cast('r.Snapshot', item_prompt(snapshots, jmespath_msg='[StartTime, OwnerId, Description]'))
    return snap


def volume_prompt(volumes: ResourceCollection) -> 'r.Volume':
    vols: List['r.Volume'] = list(volumes.all())
    return vols[0] if len(vols) == 1 else cast('r.Volume', item_prompt(volumes, jmespath_msg='Attachments[*].Device'))


def ask_to_run(msg, func):
    resp = input(f'{msg} [y/N]: ')
    if resp.lower() == 'y':
        return func()
    return None


def ask_to_create_snapshot(vol: 'r.Volume') -> 'r.Snapshot':
    return ask_to_run("No snapshots found, create one?", lambda: create_tmp_snap(vol))


def cleanup_snap(snap: 'r.Snapshot'):
    def func():
        print(f'Cleaning up snapshot: {snap.id}')
        snap.delete()

    return func


def create_tmp_snap(vol: 'r.Volume') -> 'r.Snapshot':
    instances = ', '.join([f"{a['InstanceId']} {a['Device']}" for a in vol.attachments])
    desc = f'Instance(s): {instances}, Volume: {vol.id}'
    print(f'Creating snapshot for {desc}')
    snap = vol.create_snapshot(
        Description=f'dsnap ({desc})',
        TagSpecifications=[{
            'ResourceType': 'snapshot',
            'Tags': [{'Key': 'dsnap', 'Value': 'true'}]
        }]
    )
    atexit.register(cleanup_snap(snap))
    signal.signal(signal.SIGTERM, lambda sigs, type: sys.exit())
    print("Waiting for snapshot to complete.")
    snap.wait_until_completed()
    return snap


def sha256_check(data: bytes, digest: str) -> bool:
    """Runs sha256 on data and compares it to digest, returns true if these values match.

    digest is expected to be a base64 encoded result of the binary digest.
    """
    m = hashlib.sha256()
    m.update(data)
    chksum = b64encode(m.digest()).decode()
    result = chksum == digest
    if not result:
        logging.error(f'Expected checksum {digest} but got {chksum}')
    return result

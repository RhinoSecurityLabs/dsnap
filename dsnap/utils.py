import atexit
import json
import os
import signal

import sys
from typing import TypeVar, List, Iterable
import jmespath

import typer
from typing_extensions import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r

def get_tag(tags: List[dict], key: str) -> str:
    return next(filter(lambda t: t['Key'] == 'Name', tags), '') if tags else ''


def get_name_tag(tags: List[dict]) -> str:
    return get_tag(tags, 'Name')


T = TypeVar('T')


class Item(Protocol[T]):
    id: str
    tags: List[dict]


def item_prompt(items: Iterable[Item[T]], jmespath_msg: str = None) -> T:
    """Prompt's the user for an item to select from the items passed. Item is expected to support the Item protocol."""
    if len(list(items)) == 0:
        raise UserWarning(f'No items of type {str(T)} found')
    for i, item in enumerate(items):
        if jmespath_msg:
            # dump and load json to convert datetime and similar to something readable
            data = json.loads(json.dumps(item.meta.data, default=str))
            msg = ', '.join(jmespath.search(jmespath_msg, data=data))
        name = get_name_tag(item.tags)
        print(f"{i}) {item.id} {name and f'Name: {name}, '}({jmespath_msg and str(msg)})")
    answer = int(input(f'Select {list(items)[0].meta.resource_model.name}: '))
    try:
        return list(items)[answer]
    except IndexError:
        print(f"Invalid selection, valid inputs are 0 through {len(items) - 1}", file=sys.stderr)
        return item_prompt()


def ask_to_run(msg, func):
    create = typer.confirm(msg)
    if create:
        return func()
    return None

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
        signal.signal(signal.SIGTERM, sys.exit)
        print("Waiting for snapshot to complete.")
        snap.wait_until_completed()
        return snap
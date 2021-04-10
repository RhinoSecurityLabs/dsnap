import hashlib
import logging
from base64 import b64encode
from pathlib import Path

from typing import List, Iterable, Dict, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r


def get_tag(tags: Iterable[Dict[str, str]], key: str) -> str:
    """Takes a list of tags and a key name, returns the the value for the tag with the given key name."""
    if not tags:
        return ''
    name_tag = filter(lambda t: t['Key'] == key, tags)
    return next(map(lambda t: t['Value'], name_tag), '')


def get_name_tag(tags: List[dict]) -> str:
    """Takes a list of tags and returns the value of the Name tag."""
    return get_tag(tags, 'Name')


def cleanup_snap(snap: 'r.Snapshot'):
    def func():
        print(f'Cleaning up snapshot: {snap.id}')
        snap.delete()

    return func


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


def init_vagrant(out_dir: Path = Path('.'), force=False) -> Optional[Path]:
    """Initializes out_dir directory with a templated Vagrantfile for mounting downloaded images"""
    template = Path(__file__).parent.joinpath(Path('files/Vagrantfile'))
    out = out_dir.joinpath(Path('Vagrantfile').name)
    if out.exists() and not force:
        return None
    else:
        out.write_text(template.read_text())
        return out


def fatal(*msg: str):
    logging.fatal('\n'.join(msg))
    exit(1)


def take_snapshot(vol: 'r.Volume', desc: str = '') -> 'r.Snapshot':
    if not desc:
        devices = ', '.join([a['Device'] for a in vol.attachments])
        # volumes can be attached to more then one instance at a time so include all attachments in the description
        instances = ', '.join([a['InstanceId'] for a in vol.attachments])
        desc = "Instance(s): {}, Volume: {}, Device: {}".format(instances, vol.id, devices)

    snap = vol.create_snapshot(
        Description=desc,
        TagSpecifications=[{
            'ResourceType': 'snapshot',
            'Tags': [{'Key': 'dsnap', 'Value': 'true'}]
        }]
    )
    snap.wait_until_completed()
    return snap

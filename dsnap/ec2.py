from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, List, Dict, TypeVar, Any, Protocol

import boto3.session
import boto3.resources
import botocore.config
import sys

if TYPE_CHECKING:
    from mypy_boto3_ec2 import service_resource as r
    from mypy_boto3_ec2 import type_defs as t



# class EC2:
#     def __init__(
#             self,
#             boto3_session: boto3.session.Session = boto3.session.Session(),
#             botocore_conf: Optional[botocore.config.Config] = botocore.config.Config(region_name='us-east-1')
#     ) -> None:
#         self.resource: r.EC2ServiceResource = boto3_session.resource('ec2', config=botocore_conf)
#
#     def get_instances(self, **kwargs) -> List['r.Snapshot']:
#         """Gets available instances with the current class config. Keyword args are passed through to describe_instances."""
#         return list(self.resource.instances.filter(**kwargs).all())
#
#     def get_snapshots(self, **kwargs) -> List['r.Snapshot']:
#         """Gets available snapshots with the current class config. Keyword args are passed through to describe_snapshots."""
#         return list(self.resource.snapshots.filter(**kwargs).all())
#
#     def list_snapshots(self, **kwargs) -> None:
#         print("           {}          |   {}   | {}".format('Id', 'Owner ID', 'Description'))
#         for snap in self.get_snapshots(**kwargs):
#             if format == format.list:
#                 print("{}   {}   {}".format(snap.id, snap, snap['Description']))
#             elif format == format.json:
#                 print(json.dumps(snap, default=str))
#
#     def get_snapshots(self, **kwargs) -> List['r.Snapshot']:
#         """Gets available snapshots with the current class config. Keyword args are passed through to describe_snapshots."""
#         return list(self.resource.snapshots.filter(**kwargs).all())
#

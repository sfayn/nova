# Copyright (c) 2012 OpenStack, LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Availability zone helper functions."""

from nova import db
from nova.openstack.common import cfg
from nova.openstack.common import log as logging

availability_zone_opts = [
    cfg.StrOpt('internal_service_availability_zone',
               default='internal',
               help='availability_zone to show internal services under'),
    cfg.StrOpt('default_availability_zone',
               # deprecated in Grizzly release
               deprecated_name='node_availability_zone',
               default='nova',
               help='default compute node availability_zone'),
    ]

CONF = cfg.CONF
CONF.register_opts(availability_zone_opts)

LOG = logging.getLogger(__name__)


def set_availability_zones(context, services):
    # Makes sure services isn't a sqlalchemy object
    services = [dict(service.iteritems()) for service in services]
    metadata = db.aggregate_host_get_by_metadata_key(context,
            key='availability_zone')
    for service in services:
        az = CONF.internal_service_availability_zone
        if service['topic'] == "compute":
            if metadata.get(service['host']):
                az = u','.join(list(metadata[service['host']]))
            else:
                az = CONF.default_availability_zone
        service['availability_zone'] = az
    return services


def get_host_availability_zone(context, host):
    metadata = db.aggregate_metadata_get_by_host(
        context, host, key='availability_zone')
    if 'availability_zone' in metadata:
        return list(metadata['availability_zone'])[0]
    else:
        return CONF.default_availability_zone


def get_availability_zones(context):
    """Return available and unavailable zones."""
    enabled_services = db.service_get_all(context, False)
    disabled_services = db.service_get_all(context, True)
    enabled_services = set_availability_zones(context, enabled_services)
    disabled_services = set_availability_zones(context, disabled_services)

    available_zones = []
    for zone in [service['availability_zone'] for service
                 in enabled_services]:
        if not zone in available_zones:
            available_zones.append(zone)

    not_available_zones = []
    zones = [service['available_zones'] for service in disabled_services
            if service['available_zones'] not in available_zones]
    for zone in zones:
        if zone not in not_available_zones:
            not_available_zones.append(zone)
    return (available_zones, not_available_zones)

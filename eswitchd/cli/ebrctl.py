#!/usr/bin/python

import re
import sys
from eswitchd.cli import conn_utils
from eswitchd.cli import exceptions
from eswitchd.common import constants

IB_PREFIX = "/sys/class/infiniband"
pkeys_id_pattern = "%s/[^/]+/iov/[^/]+/ports/[^/]+/pkey_idx/[^/]+$" % IB_PREFIX
admin_guids_pattern = "%s/[^/]+/iov/ports/[^/]+/admin_guids/[^/]+$" % IB_PREFIX
files_pattern = "(%s)|(%s)" % (pkeys_id_pattern, admin_guids_pattern)

action = sys.argv[1]
client = conn_utils.ConnUtil()


def main():
    if action == 'allocate-port':
        vnic_mac = sys.argv[2]
        device_id = sys.argv[3]
        fabric = sys.argv[4]
        vnic_type = sys.argv[5]
        try:
            dev = client.allocate_nic(vnic_mac, device_id, fabric, vnic_type)
        except exceptions.MlxException as e:
            sys.stderr.write("Error in allocate command")
            sys.stderr.write(e.message)
            sys.exit(1)
        sys.stdout.write(dev)
        sys.exit(0)

    elif action == 'add-port':
        vnic_mac = sys.argv[2]
        device_id = sys.argv[3]
        fabric = sys.argv[4]
        vnic_type = sys.argv[5]
        dev_name = sys.argv[6]
        try:
            if vnic_type in (constants.VIF_TYPE_DIRECT,
                             constants.VIF_TYPE_MLNX_DIRECT):
                vnic_type = constants.VIF_TYPE_DIRECT
            dev = client.plug_nic(vnic_mac, device_id, fabric,
                                  vnic_type, dev_name)

        except exceptions.MlxException as e:
            sys.stderr.write("Error in add-port command")
            sys.stderr.write(e.message)
            sys.exit(1)
        sys.stdout.write(dev)
        sys.exit(0)

    elif action == 'del-port':
        fabric = sys.argv[2]
        vnic_mac = sys.argv[3]
        try:
            client.deallocate_nic(vnic_mac, fabric)
        except exceptions.MlxException as e:
            sys.stderr.write("Error in del-port command")
            sys.stderr.write(e.message)
            sys.exit(1)
        sys.exit(0)

    elif action == 'write-sys':
        path = sys.argv[2]
        value = sys.argv[3]
        if re.match(files_pattern, path):
            try:
                fd = open(path, 'w')
                fd.write(value)
                fd.close()
            except Exception as e:
                sys.stderr.write("Error in write-sys command")
                sys.stderr.write(e.message)
                sys.exit(1)
            sys.exit(0)
        else:
            sys.stderr.write("Path %s is not valid for this action" % path)
            sys.exit(1)

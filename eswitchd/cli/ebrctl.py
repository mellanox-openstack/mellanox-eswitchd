#!/usr/bin/python

import sys
from eswitchd.cli import conn_utils
from eswitchd.cli import exceptions
from eswitchd.common import constants

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
            if vnic_type in (constants.VIF_TYPE_DIRECT, constants.VIF_TYPE_MLNX_DIRECT):
                vnic_type = constants.VIF_TYPE_DIRECT
            dev = client.plug_nic(vnic_mac, device_id, fabric, vnic_type, dev_name)
                
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

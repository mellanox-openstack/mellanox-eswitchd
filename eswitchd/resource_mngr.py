# Copyright 2013 Mellanox Technologies, Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import glob
from lxml import etree
import os

import libvirt
from oslo_log import log as logging


from common import constants
from common import exceptions
from db import device_db
from utils import pci_utils

LOG = logging.getLogger(__name__)

NET_PATH = "/sys/class/net/"

class ResourceManager:
    def __init__(self):
        self.pci_utils = pci_utils.pciUtils()
        self.device_db = device_db.DeviceDB()

    def add_fabric(self, fabric, pf, fabric_type):
        pci_id, hca_port, pf_mlx_dev = self._get_pf_details(pf)
        self.device_db.add_fabric(fabric, pf, pci_id, hca_port, fabric_type, pf_mlx_dev)
        vfs = self.discover_devices(pf,hca_port)
        LOG.info("PF %s, vfs=%s" % (pf, vfs))
        self.device_db.set_fabric_devices(fabric, vfs)

    def scan_attached_devices(self):
        devices = []
        vm_ids = {}
        conn = libvirt.openReadOnly('qemu:///system')
        domains = []
        self.macs_map = self._get_vfs_macs()
        domains_names = conn.listDefinedDomains()
        defined_domains = map(conn.lookupByName, domains_names)
        domains_ids = conn.listDomainsID()
        running_domains = map(conn.lookupByID, domains_ids)
        for domain in defined_domains:
            [state, maxmem, mem, ncpu, cputime] = domain.info()
            if state in (libvirt.VIR_DOMAIN_PAUSED,
                         libvirt.VIR_DOMAIN_SHUTDOWN,
                         libvirt.VIR_DOMAIN_SHUTOFF):
                domains.append(domain)
        domains += running_domains

        for domain in domains:
            raw_xml = domain.XMLDesc(0)
            tree = etree.XML(raw_xml)
            hostdevs   = tree.xpath("devices/hostdev/source/address")
            vm_id = tree.find('uuid').text
            for dev in self._get_attached_hostdevs(hostdevs):
                devices.append(dev)
                vm_ids[dev[0]] = vm_id
        return devices, vm_ids

    def get_fabric_pf(self,fabric):
        return self.device_db.get_pf(fabric)

    def get_fabric_details(self, fabric):
        return self.device_db.get_fabric_details(fabric)

    def discover_devices(self, pf, hca_port):
        vfs = list()
        vfs_paths = glob.glob(NET_PATH + pf + "/device/virtfn*")
        for vf_path in vfs_paths:
            path = vf_path+'/net'
            if not os.path.isdir(path):
                vf = os.readlink(vf_path).strip('../')
                vfs.append(vf)
        return vfs

    def get_free_vfs(self,fabric):
        return self.device_db.get_free_vfs(fabric)

    def get_free_devices(self,fabric):
        return self.device_db.get_free_devices(fabric)

    def allocate_device(self, fabric, dev=None):
        try:
            dev = self.device_db.allocate_device(fabric,dev)
            return dev
        except Exception:
            raise exceptions.MlxException('Failed to allocate device')

    def deallocate_device(self, fabric, dev):
        try:
            dev = self.device_db.deallocate_device(fabric, dev)
            return dev
        except Exception:
            return None

    def get_fabric_for_dev(self, dev):
        return self.device_db.get_dev_fabric(dev)

    def _get_vfs_macs(self):
        macs_map = {}
        fabrics = self.device_db.device_db.keys()
        for fabric in fabrics:
            fabric_details = self.device_db.get_fabric_details(fabric)
            pf = fabric_details['pf']
            fabric_type = fabric_details['fabric_type']
            hca_port = fabric_details['hca_port']
            pf_mlx_dev = fabric_details['pf_mlx_dev']
            try:
                macs_map[fabric] = self.pci_utils.get_vfs_macs_ib(pf, pf_mlx_dev, hca_port)
            except Exception:
                LOG.warning("Failed to get vfs macs for fabric %s ",fabric)
                continue
        return macs_map

    def _get_attached_hostdevs(self, hostdevs):
        devs = []
        for hostdev in hostdevs:
            dev = self.pci_utils.get_device_address(hostdev)
            fabric = self.get_fabric_for_dev(dev)
            if fabric:
                fabric_details = self.get_fabric_details(fabric)
                hca_port = fabric_details['hca_port']
                pf_mlx_dev = fabric_details['pf_mlx_dev']
                vf_index = self.pci_utils.get_vf_index(pf_mlx_dev, dev, hca_port)
                try:
                    mac = self.macs_map[fabric][str(vf_index)]
                    devs.append((dev,mac,fabric))
                except KeyError:
                    LOG.warning("Failed to retrieve Hostdev MAC for dev %s",dev)
            else:
                LOG.info("No Fabric defined for device %s",hostdev)
        return devs

    def _get_pf_details(self,pf):
        hca_port = self.pci_utils.get_eth_port(pf)
        pci_id  = self.pci_utils.get_pf_pci(pf)
        pf_pci_id  = self.pci_utils.get_pf_pci(pf, type='normal')
        pf_mlx_dev = self.pci_utils.get_pf_mlx_dev(pf_pci_id)
        return (pci_id, hca_port, pf_mlx_dev)

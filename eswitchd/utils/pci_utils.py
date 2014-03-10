# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import ethtool
import glob
import logging
import os
import re
import sys
from command_utils import execute
from eswitchd.common import constants

LOG = logging.getLogger('eswitchd')

class pciUtils:
    NET_PATH =  "/sys/class/net/"
    VF_PF_NETDEV =  "/sys/bus/pci/devices/VF/physfn/net"
    ETHS_PATH = "/sys/class/net/eth*"
    ETH_PF_NETDEV = "/sys/class/net/DEV/device/physfn/net"
    ETH_PATH = "/sys/class/net/ETH"
    IBS_PATH = "/sys/class/net/ib*"
    ETH_PF_NETDEV = "/sys/class/net/DEV/device/physfn/net"
    ETH_DEV =  ETH_PATH + "/device"
    ETH_MAC =  ETH_PATH + "/address"
    ETH_PORT = ETH_PATH + "/dev_id"
    LINK_PATH = ETH_PATH + "/carrier"
    PF_MLX_DEV_PATH = "/sys/class/infiniband/*"
    VENDOR_PATH = ETH_DEV + '/vendor'

    VF_BIND_PATH =  "/sys/bus/pci/drivers/mlx4_core/bind"
    VF_UNBIND_PATH =  "/sys/bus/pci/drivers/mlx4_core/unbind"
    VFS_PATH = ETH_DEV + "/virtfn*"

   
    def __init__(self):
        pass
 
    def get_dev_attr(self, attr_path):
        """
        @param attr_path: The full path of the attribute of the device
        @return: The content of the first line or None if file not found
        """
        try:
            fd = open(attr_path)
            return fd.readline().strip()
        except IOError:
            return 

    def verify_vendor_pf(self, pf, vendor_id = constants.VENDOR):
        """
	Verify that PF has the specified vendor id
	"""
        vendor_path = pciUtils.VENDOR_PATH.replace("ETH", pf)
        if self.get_dev_attr(vendor_path) == vendor_id:
	        return True
        else:
            return False

    def is_sriov_pf(self, pf):
        vfs_path = pciUtils.VFS_PATH.replace("ETH", pf)
        vfs = glob.glob(vfs_path)
        if vfs:
            return True
        else:
            return 
        
    def get_interface_type(self, ifc):
        cmd = ['ip', '-o', 'link', 'show', 'dev', ifc]
        try:
            result = execute(cmd, root_helper=None)
        except Exception,e:
            LOG.warning("Failed to execute command %s due to %s",cmd,e)
            raise
        if result.find('link/ether') != -1:
            return 'eth'
        elif result.find('link/infiniband') != -1:
            return 'ib'
        else:
            return None

    def is_ifc_module(self, ifc, fabric_type):
        modules = {'eth':'mlx4_en', 'ib':'ipoib'}
        if modules[fabric_type] in ethtool.get_module(ifc):
            return True
        
    def filter_ifcs_module(self, ifcs, fabric_type):
        return [ifc for ifc in ifcs if self.is_ifc_module(ifc, fabric_type)]

    def get_auto_pf(self, fabric_type):
        ifcs = ethtool.get_devices()
        pfs = filter(self.verify_vendor_pf, ifcs) 
        pfs = filter(self.is_sriov_pf, pfs)
        pfs = self.filter_ifcs_module(pfs, fabric_type)
        if len(pfs) != 1:
            LOG.error("Multiple PFs found %s.Configure Manually." % pfs)
            sys.exit(1)
        return pfs[0]

    def get_eth_mac(self, dev):
        mac_path = self.ETH_MAC.replace("ETH", dev)
        return self.get_dev_attr(mac_path)
     
    def get_eth_vf(self, dev):
        """
        @param dev: Ethetnet device
        @return: VF of Ethernet device
        """
        vf_path = pciUtils.ETH_DEV.replace("ETH", dev)
        try:
            device = os.readlink(vf_path)
            vf = device.split('/')[3]
            return vf
        except:
            return None

    def get_pf_pci(self, pf,type=None):
        vf = self.get_eth_vf(pf)
        if vf:
            if type == 'normal':
               return vf
            else:
               return vf[:-2]
        else:
            return None

    def get_pf_mlx_dev(self, pci_id):
        paths = glob.glob(pciUtils.PF_MLX_DEV_PATH)
        for path in paths:
            id = os.readlink(path).split('/')[5]
            if pci_id == id:
                return path.split('/')[-1]

    def get_vf_index(self, dev, dev_type):
        """
        @param dev: Ethernet device or VF
        @param dev_type: 'direct' or 'hostdev'        
        @return: VF index 
        """
        if dev_type == 'direct':
            dev = self.get_eth_vf(dev)
        if dev:
            vf_index = self._calc_vf_index(dev)
            return vf_index
        return None
   
    def get_eth_port(self, dev):
        port_path = pciUtils.ETH_PORT.replace("ETH", dev)
        try:
            with open(port_path) as f:
                dev_id = int(f.read(),0)
                return dev_id+1
        except IOError:
            return

    def get_vfs_macs(self,pf):
        macs_map = {}
        vf_mac_pattern = re.compile("vf\s+(\d+)\s+MAC\s+(\S+)\,")
        cmd = ['ip', 'link', 'show', 'dev', pf]
        try:
            result = execute(cmd, root_helper=None)
            for line in result.splitlines():
                match = vf_mac_pattern.search(line)
                if match:
                    vf_index, mac = match.groups()
                    macs_map[vf_index] = mac  
        except Exception,e:
            LOG.warning("Failed to execute command %s due to %s",cmd,e)
            raise
        return macs_map                  

    def get_vfs_macs_ib(self, pf, pf_mlx_dev, hca_port):
        macs_map = {}
        guids_path = constants.ADMIN_GUID_PATH % (pf_mlx_dev, hca_port, '[1-9]*')
        paths = glob.glob(guids_path)
        for path in paths:
            vf_index = path.split('/')[-1]
            with open(path) as f:
                guid = f.readline().strip()
                if guid == constants.INVALID_GUID:
                    mac = constants.INVALID_MAC
                else: 
                    head = guid[:6]
                    tail = guid[-6:]
                    mac = ":".join(re.findall('..?', head + tail))
                macs_map[str(int(vf_index)-1)] = mac 
        return macs_map

    def get_device_address(self, hostdev):
        domain = hostdev.attrib['domain'][2:]
        bus = hostdev.attrib['bus'][2:]
        slot = hostdev.attrib['slot'][2:]
        function = hostdev.attrib['function'][2:]
        dev = "%.4s:%.2s:%2s.%.1s" %(domain,bus,slot,function)
        return dev
    
    def _calc_vf_index(self, dev):
        vf_address = re.split(r"\.|\:", dev)
        vf_index = int(vf_address[2]) * 8 + int(vf_address[3]) - 1
        return vf_index

    def set_vf_binding(self, vf, is_bind=False):
        if is_bind:
            cmd = ["echo", vf, ">",pciUtils.VF_BIND_PATH]
        else:
            cmd = ["echo", vf, ">",pciUtils.VF_UNBIND_PATH]
        try:
            result = execute(cmd, root_helper=None)
        except Exception,e:
            LOG.warning("Failed to execute command %s due to %s",cmd,e)
            raise

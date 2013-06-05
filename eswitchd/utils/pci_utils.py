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

import glob
import os
import re
import logging
from command_utils import execute
from eswitchd.common import constants

LOG = logging.getLogger('eswitchd')

class pciUtils:
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
    constants.SUBS_DEV_PATH = ETH_DEV + '/subsystem_device'
    constants.VENDOR_PATH = ETH_DEV + '/vendor'

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

    def get_pf(self, fabric_type):
        """
        Scan the system to find a PF with state UP
        """
        if fabric_type == 'ib':
            eths = glob.glob(self.IBS_PATH)
        else:
            eths = glob.glob(self.ETHS_PATH)
        pfs = []
        for eth in eths:
            eth = eth.split('/')[-1]
            vendor_path = constants.VENDOR_PATH.replace("ETH", eth)
            subs_dev_path = constants.SUBS_DEV_PATH.replace("ETH", eth)

            if self.get_dev_attr(vendor_path) == constants.VENDOR:
                if self.get_dev_attr(subs_dev_path) == constants.SUBS_DEV:
                    pfs.append(eth)

        if not pfs:
            LOG.debug("No PF was found!")
            return 
        else:
           pfs_with_vfs = []
           for pf in pfs:
               vfs_path = pciUtils.VFS_PATH.replace("ETH", pf)
               vfs = glob.glob(vfs_path)
               if vfs:
                   pfs_with_vfs.append(pf)
        if not pfs_with_vfs:
            LOG.debug("No PF with VFs was found! "+
                      "Did you configure SR-IOV in /etc/modprobe.d/mlx4_core.conf?")
            return 
        elif len(pfs_with_vfs) == 1:
            return pfs_with_vfs[0]
        else:
            pfs_up = []
            for pf in pfs:
                link_path = pciUtils.LINK_PATH.replace("ETH", pf)
                if self.get_dev_attr(link_path) == constants.LINK_UP:
                    pfs_up.append(pf)
        if pfs_up:
            if len(pfs_up) > 1:
                LOG.debug("Found the following PFs up: %s\nPlease configure one of them in the configuration file\n" % ",".join(pfs_up))
            else:
                LOG.debug("PF is %s" % pfs_up[0])
                return pfs_up[0]
        else:
            LOG.debug("None of the PFs: %s is up!" % ",".join(pfs))
            return

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

    def get_pf_pci(self, pf):
        vf = self.get_eth_vf(pf)
        if vf:
            return vf[:-2]
        else:
            return None

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
            result = execute(cmd, root_helper='sudo')
            for line in result.splitlines():
                match = vf_mac_pattern.search(line)
                if match:
                    vf_index, mac = match.groups()
                    macs_map[vf_index] = mac  
        except Exception,e:
            LOG.warning("Failed to execute command %s due to %s",cmd,e)
            raise
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
            result = execute(cmd, root_helper='sudo')
        except Exception,e:
            LOG.warning("Failed to execute command %s due to %s",cmd,e)
            raise

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

import os
import re
from nova.openstack.common import log as logging
from utils.command_utils import execute

LOG = logging.getLogger('mlnx_daemon')

class pciUtils:
    VF_PF_NETDEV =  "/sys/bus/pci/devices/VF/physfn/net"
    ETH_PF_NETDEV = "/sys/class/net/DEV/device/physfn/net"
    ETH_VF =        "/sys/class/net/ETH/device"
    ETH_PORT =      "/sys/class/net/ETH/dev_id"
    VF_BIND_PATH =  "/sys/bus/pci/drivers/mlx4_core/bind"
    VF_UNBIND_PATH =  "/sys/bus/pci/drivers/mlx4_core/unbind"
   
    def __init__(self):
        pass
       
    def get_eth_vf(self, dev):
        """
        @param dev: Ethetnet device
        @return: VF of Ethernet device
        """
        vf_path = pciUtils.ETH_VF.replace("ETH", dev)
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
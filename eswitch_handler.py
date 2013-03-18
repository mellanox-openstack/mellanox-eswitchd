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

from nova.openstack.common import log as logging
from utils import pci_utils
from utils.command_utils import execute
from db import eswitch_db
from resource_mngr import ResourceManager 
from common.exceptions import MlxException
from common import constants

DEFAULT_MAC_ADDRESS = '00:00:00:00:00:01'
LOG = logging.getLogger('mlnx_daemon')
#LOG = logging.getLogger(__name__)

class eSwitchHandler(object):
    def __init__(self,fabrics=None):
        self.eswitches = {}
        self.pci_utils = pci_utils.pciUtils()
        self.rm = ResourceManager()
        self.devices = {
                        constants.VIF_TYPE_DIRECT: set(),
                        constants.VIF_TYPE_HOSTDEV:set()
                        }
        if fabrics:
            self.add_fabrics(fabrics)
    
    def add_fabrics(self,fabrics):
        for fabric, pf in fabrics:
            self.eswitches[fabric] = eswitch_db.eSwitchDB()
            self._add_fabric(fabric,pf)
        self.sync_devices()  
          
    def sync_devices(self):
        devices = self.rm.scan_attached_devices()
        added_devs = {}
        removed_devs = {}
        for type, devs in devices.items():
            added_devs[type] = set(devs)-self.devices[type]
            removed_devs[type] = self.devices[type]-set(devs)      
            self._treat_added_devices(added_devs[type],type)
            self._treat_removed_devices(removed_devs[type],type)
            self.devices[type] = set(devices[type])

    def _add_fabric(self,fabric,pf):
        self.rm.add_fabric(fabric,pf)
        vfs = self.rm.get_free_vfs(fabric)
        eths = self.rm.get_free_eths(fabric)
        for vf in vfs:
            self.eswitches[fabric].create_port(vf, constants.VIF_TYPE_HOSTDEV)
        for eth in eths:
            self.eswitches[fabric].create_port(eth, constants.VIF_TYPE_DIRECT)

    def _treat_added_devices(self, devices,dev_type):
        for dev, mac, fabric in devices:
            if fabric:
                self.rm.allocate_device(fabric, dev_type=dev_type, dev=dev)
                self.eswitches[fabric].attach_vnic(port_name=dev, device_id=None, vnic_mac=mac)
                self.eswitches[fabric].plug_nic(port_name=dev)
            else:
                LOG.debug("No Fabric defined for device %s", dev)
                
    def _treat_removed_devices(self,devices,dev_type):
        for dev, mac in devices:
            fabric = self.rm.get_fabric_for_dev(dev)
            if fabric:
                self.rm.deallocate_device(fabric, dev_type=dev_type, dev=dev)
                self.eswitches[fabric].detach_vnic(vnic_mac=mac)
            else:
                LOG.debug("No Fabric defined for device %s", dev)


#-------------------------------------------------
#  requests handling
#-------------------------------------------------

    def set_fabric_mapping(self, fabric, interface):
        dev = self.rm.get_fabric_for_dev(interface)
        if not dev:
            fabrics = [(fabric, interface)]
            self.add_fabrics(fabrics)
            dev = interface
        return (fabric, interface)
           
    def get_vnics(self, fabrics):
        vnics = {}
        for fabric in fabrics:
            eswitch = self._get_vswitch_for_fabric(fabric)
            if eswitch:
                vnics_for_eswitch = eswitch.get_attached_vnics()
                vnics.update(vnics_for_eswitch)
            else:
                LOG.error("No eSwitch found for Fabric %s",fabric)
                continue
        LOG.debug("vnics are %s",vnics)
        return vnics  

    def create_port(self, fabric, vnic_type, device_id, vnic_mac):
        dev = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if not dev:
                try:
                    dev = self.rm.allocate_device(fabric, vnic_type)
                    if eswitch.attach_vnic(dev, device_id, vnic_mac):
                        if vnic_type == constants.VIF_TYPE_HOSTDEV:
                            pf, vf_index = self._get_device_pf_vf(fabric, vnic_type, dev)
                            self._config_vf_mac_address(pf, vf_index, vnic_mac)
                    else:
                        raise MlxException('Failed to attach vnic')
                except (RuntimeError, MlxException):
                    LOG.error('Create port operation failed ')
                    self.rm.deallocate_device(fabric,vnic_type,dev)
                    dev = None                                
        else:
            LOG.error("No eSwitch found for Fabric %s",fabric)
        return dev
    
    def plug_nic(self, fabric, device_id, vnic_mac):
        dev = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if dev:
                eswitch.plug_nic(dev)
        else:
            LOG.error("No eSwitch found for Fabric %s",fabric)
        return dev

         
    def delete_port(self, fabric, vnic_mac):
        """
        @note: Free Virtual function associated with vNIC MAc
        """
        dev = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.detach_vnic(vnic_mac)
            if dev:
                dev_type = eswitch.get_dev_type(dev)
                if dev_type == constants.VIF_TYPE_HOSTDEV:
                    pf, vf_index = self._get_device_pf_vf(fabric, dev_type, dev)
                    #unset MAC to default value
                    self._config_vf_mac_address(pf, vf_index, DEFAULT_MAC_ADDRESS)
                self.rm.deallocate_device(fabric,dev_type,dev)
        else:
            LOG.error("No eSwitch found for Fabric %s",fabric)
        return dev  

    def port_release(self, fabric, vnic_mac):
        """
        @todo: handle failures
        """
        ret = self.set_vlan(fabric, vnic_mac, constants.UNTAGGED_VLAN_ID)
        self.port_down(fabric, vnic_mac)
        eswitch = self._get_vswitch_for_fabric(fabric)
        eswitch.port_release(vnic_mac)
        return ret
    
    def port_down(self,fabric,vnic_mac):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if dev: 
                self._config_port_down(dev)
            else:
                LOG.debug("No device for MAC %s",vnic_mac)
                
    def set_vlan(self, fabric, vnic_mac, vlan):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            eswitch.set_vlan(vnic_mac, vlan)
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            state = eswitch.get_port_state(dev)
            if dev:
                if state in (constants.VPORT_STATE_ATTACHED, constants.VPORT_STATE_UNPLUGGED):
                    vnic_type = eswitch.get_port_type(dev)
                    pf, vf_index = self._get_device_pf_vf(fabric, vnic_type, dev)
                    if pf and vf_index:
                        try:
                            if vnic_type == constants.VIF_TYPE_DIRECT:
                                self._config_vlan_priority_direct(pf, vf_index, dev, vlan)
                            else:
                                self._config_vlan_priority_hostdev(pf, vf_index, dev, vlan)
                            return True
                        except RuntimeError:
                            LOG.error('Set VLAN operation failed')    
                    else:
                        LOG.error('Invalid VF/PF index for device %s',dev)         
        return False           
            
    def _get_vswitch_for_fabric(self, fabric):
        if fabric in self.eswitches:
            return self.eswitches[fabric]
        else:
            return 
    
    def _get_device_pf_vf(self, fabric, vnic_type, dev):
        pf = self.rm.get_fabric_pf(fabric)
        vf_index = self.pci_utils.get_vf_index(dev, vnic_type)
        return pf, vf_index
     
    def _config_vf_mac_address(self,pf,vf_index,vnic_mac):
        cmd = ['ip', 'link','set',pf, 'vf', vf_index ,'mac',vnic_mac]
        execute(cmd, root_helper='sudo')
            
    def _config_vlan_priority_direct(self, pf, vf_index, dev, vlan,priority='0'):
        vf = self.pci_utils.get_eth_vf(dev)
        self._config_port_down(dev)
        cmd = ['ip', 'link','set',pf , 'vf', vf_index, 'vlan', vlan, 'qos', priority]
        execute(cmd, root_helper='sudo')
        self._config_port_up(dev)
        
    def _config_vlan_priority_hostdev(self, pf, vf_index, dev, vlan,priority='0'):
        cmd = ['ip', 'link','set',pf , 'vf', vf_index, 'vlan', vlan, 'qos', priority]
        execute(cmd, root_helper='sudo')

    def _config_port_down(self,dev):
        cmd = ['ip', 'link', 'set', dev, 'down']       
        execute(cmd, root_helper='sudo')
        
    def _config_port_up(self,dev):
        cmd = ['ip', 'link', 'set', dev, 'up']       
        execute(cmd, root_helper='sudo')        
        

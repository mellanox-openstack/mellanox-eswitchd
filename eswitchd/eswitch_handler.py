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

#from nova.openstack.common import log as logging
import glob
import logging
import sys
from acl_handler import EthtoolAclHandler
from common.exceptions import MlxException
from common import constants
from common import config
from oslo.config import cfg
from db import eswitch_db
from of_handler import OfHandler
from resource_mngr import ResourceManager 
from utils import pci_utils
from utils.command_utils import execute

DEFAULT_MAC_ADDRESS = '00:00:00:00:00:01'
LOG = logging.getLogger('eswitchd')
INVALID_PKEY = 'none'
DEFAULT_PKEY_IDX = '0'
PARTIAL_PKEY_IDX = '1'
BASE_PKEY = '0x8000'
PADDING = '0000' 
PARTIAL_VLAN = -1
ACL_REF = 0

class eSwitchHandler(object):
    def __init__(self,fabrics=None):
        self.acl_handler = EthtoolAclHandler()
        self.eswitches = {}
        self.pci_utils = pci_utils.pciUtils()
        self.rm = ResourceManager()
        self.devices = {
                        constants.VIF_TYPE_DIRECT: set(),
                        constants.VIF_TYPE_HOSTDEV:set()
        }
        if cfg.CONF.OF.start_of_agent:
            self.of_handler = OfHandler()
        if fabrics:
            self.add_fabrics(fabrics)

    def add_fabrics(self, fabrics):
        res_fabrics = []
        for fabric, pf in fabrics:
            fabric_type = None
            
            if pf in ('autoib', 'autoeth'):
                fabric_type = pf.replace('auto', '')
                pf = self.pci_utils.get_pf(fabric_type)
            else:
                for type in ("ib", "eth"):
                    if pf.startswith(type):
                        fabric_type = type
            if fabric_type:
                self.eswitches[fabric] = eswitch_db.eSwitchDB()
                self._add_fabric(fabric, pf, fabric_type)
                res_fabrics.append((fabric, pf, fabric_type))
            else:
                LOG.debug("Problem with PF=auto.Terminating!")
                sys.exit(1)
        self.sync_devices()  
        if hasattr(self, 'of_handler'):
            self.of_handler.add_fabrics(res_fabrics)
          
    def sync_devices(self):
        devices, vm_ids = self.rm.scan_attached_devices()
        added_devs = {}
        removed_devs = {}
        for type, devs in devices.items():
            added_devs[type] = set(devs)-self.devices[type]
            removed_devs[type] = self.devices[type]-set(devs)      
            self._treat_added_devices(added_devs[type], type, vm_ids)
            self._treat_removed_devices(removed_devs[type], type)
            self.devices[type] = set(devices[type])

    def _add_fabric(self, fabric, pf, fabric_type):
        self.rm.add_fabric(fabric, pf, fabric_type)
        self._config_port_up(pf)
        vfs = self.rm.get_free_vfs(fabric)
        eths = self.rm.get_free_eths(fabric)
        
        for vf in vfs:
            self.eswitches[fabric].create_port(vf, constants.VIF_TYPE_HOSTDEV)
        for eth in eths:
            self.eswitches[fabric].create_port(eth, constants.VIF_TYPE_DIRECT)

    def _treat_added_devices(self, devices,dev_type, vm_ids):
        for dev, mac, fabric in devices:
            if fabric:
                self.rm.allocate_device(fabric, dev_type=dev_type, dev=dev)
                self.eswitches[fabric].attach_vnic(port_name=dev, device_id=vm_ids[dev], vnic_mac=mac)
                if self.eswitches[fabric].vnic_exists(mac):
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

    def create_port(self, fabric, vnic_type, device_id, vnic_mac,dev_name):
        dev = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if not dev:
                try:
                    dev = self.rm.allocate_device(fabric, vnic_type)
                    if eswitch.attach_vnic(dev, device_id, vnic_mac,dev_name):
                        pf, vf_index = self._get_device_pf_vf(fabric, vnic_type, dev)
                        if vnic_type == constants.VIF_TYPE_HOSTDEV:
                            self._config_vf_mac_address(fabric, dev, vf_index, vnic_mac)
                        else:
                            self._set_devname(dev_name, dev)    
                        acl_rules = eswitch.get_acls_for_vnic(vnic_mac)
                        self.acl_handler.set_acl_rules(pf, acl_rules)
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
            if not dev:
                #check for port_table entry with device_id and INVALID_MAC
                for key, data in eswitch.port_table.items():
                    if data['device_id'] == device_id and data['vnic'] == constants.INVALID_MAC:
                        dev = key
                        break
                else:
                    LOG.error("Plug NIC: Didn't find dev for MAC:%s and device_id:%s" % (data['vnic'], device_id))
                if dev:
                    eswitch.port_table[dev]['vnic'] = vnic_mac
                    eswitch.port_policy.update({vnic_mac: {'vlan':None,
                                                        'dev':dev,
                                                        'device_id':device_id,
                                                        'flow_ids':set([]),
                                                        'priority': 0,
                                                        }}) 
                    pf, vf_index = self._get_device_pf_vf(fabric, constants.VIF_TYPE_HOSTDEV, dev)
                    self._config_vf_mac_address(fabric, dev, vf_index, vnic_mac)      
                else:
                    return None           
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
            dev_name = eswitch.get_dev_alias_for_vnic(vnic_mac)
            dev = eswitch.detach_vnic(vnic_mac)
            if dev:
                dev_type = eswitch.get_dev_type(dev)
                if dev_type == constants.VIF_TYPE_HOSTDEV:
                    pf, vf_index = self._get_device_pf_vf(fabric, dev_type, dev)
                    #unset MAC to default value
                    self._config_vf_mac_address(fabric, dev, vf_index, DEFAULT_MAC_ADDRESS)
                if dev_name:    
                    self._set_devname(dev, dev_name)
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
                vnic_type = eswitch.get_port_type(dev)
                self._config_port_down(dev, vnic_type)
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
                    priority = eswitch.get_priority(vnic_mac)
                    vnic_type = eswitch.get_port_type(dev)
                    if eswitch.get_port_table()[dev]['alias']:
                        dev = eswitch.get_port_table()[dev]['alias']

                    pf, vf_index = self._get_device_pf_vf(fabric, vnic_type, dev)
                    if pf and vf_index is not None:
                        try:
                            if vnic_type == constants.VIF_TYPE_DIRECT:
                                self._config_vlan_priority_direct(pf, vf_index, dev, vlan, priority)
                            else:
                                self._config_vlan_priority_hostdev(fabric, pf,  vf_index, dev, vlan, priority)
                            return True
                        except RuntimeError:
                            LOG.error('Set VLAN operation failed')    
                    else:
                        LOG.error('Invalid VF/PF index for device %s,PF-%s,VF Index - %s',dev, pf, vf_index)         
        return False           
    
    def set_priority(self, fabric, vnic_mac, priority):
        ret = False
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            vlan = eswitch.set_priority(vnic_mac, priority)
            if vlan:
                ret = self.set_vlan(fabric, vnic_mac, vlan)
        return ret
                
    def set_acl_rule(self, fabric, vnic_mac, params):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            pf = self.rm.get_fabric_pf(fabric)
            flow_id, acl_rule = self.acl_handler.build_acl_rule(params)
            if acl_rule:
                eswitch.set_acl_rule(vnic_mac, acl_rule, flow_id)
                vnic_state = eswitch.get_vnic_state(vnic_mac)
                if vnic_state in  (constants.VPORT_STATE_ATTACHED,constants.VPORT_STATE_PENDING):
                    try:
                        acl_ref = self.acl_handler.set_acl_rule(pf, acl_rule)
                        eswitch.update_acl_rule_ref(flow_id, acl_ref)
                        return True
                    except RuntimeError:
                        LOG.error('Failed to set ACL rule flow_id-%s', flow_id)
        return False
        
    def delete_acl_rule(self, fabric, flow_id):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            pf = self.rm.get_fabric_pf(fabric)
            (ref, vnic_mac) = eswitch.del_acl_rule(flow_id)
            if ref:
                try:
                    self.acl_handler.del_acl_rule(pf, ref)
                    return True
                except RuntimeError:
                    LOG.error('Failed to delete ACL flow_id-%s', flow_id)
        return False
    
    def update_flow_id(self, fabric, old_flow_id, new_flow_id):
        ret = False
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            ret = eswitch.update_flow_id(old_flow_id, new_flow_id)
        return ret

    def _get_vswitch_for_fabric(self, fabric):
        if fabric in self.eswitches:
            return self.eswitches[fabric]
        else:
            return 
    
    def _get_device_pf_vf(self, fabric, vnic_type, dev):
        pf = self.rm.get_fabric_pf(fabric)
        vf_index = self.pci_utils.get_vf_index(dev, vnic_type)
        return pf, vf_index
     
    def _config_vf_pkey(self, ppkey_idx, pkey_idx, pf_mlx_dev, vf_pci_id, hca_port):
        path = "/sys/class/infiniband/%s/iov/%s/ports/%s/pkey_idx/%s" % (pf_mlx_dev, vf_pci_id, hca_port, pkey_idx)
        fd = open(path, 'w')
        fd.write(ppkey_idx)
        fd.close()

    def _get_guid_from_mac(self, mac):
        if mac == DEFAULT_MAC_ADDRESS:
            return constants.INVALID_GUID
        mac = mac.replace(':','')
        prefix = mac[:6]
        suffix = mac[6:]
        guid = prefix + PADDING + suffix
        return guid
 
    def _config_vf_mac_address(self, fabric, dev, vf_index, vnic_mac):
        vguid = self._get_guid_from_mac(vnic_mac)
        fabric_details = self.rm.get_fabric_details(fabric)
        pf = fabric_details['pf'] 
        fabric_type = fabric_details['fabric_type']
        if fabric_type == 'ib':
            hca_port = fabric_details['hca_port'] 
            pf_mlx_dev = fabric_details['pf_mlx_dev'] 

            self._config_vf_pkey(INVALID_PKEY, DEFAULT_PKEY_IDX, pf_mlx_dev, dev, hca_port)
            path = "/sys/class/infiniband/%s/iov/ports/%s/admin_guids/%s" % (pf_mlx_dev, hca_port, int(vf_index)+1)
            fd = open(path, 'w')
            fd.write(vguid)
            fd.close()
            ppkey_idx = self._get_pkey_idx(PARTIAL_VLAN, pf_mlx_dev, hca_port)
            if ppkey_idx >= 0:
                self._config_vf_pkey(ppkey_idx, PARTIAL_PKEY_IDX, pf_mlx_dev, dev, hca_port)
            else:
                LOG.error("Can't find partial management pkey for %s:%s" % (pf_mlx_dev,vf_index))

        else:
            cmd = ['ip', 'link','set',pf, 'vf', vf_index ,'mac',vnic_mac]
            execute(cmd, root_helper='sudo')
            
    def _config_vlan_priority_direct(self, pf, vf_index, dev, vlan,priority='0'):
        self._config_port_down(dev)
        cmd = ['ip', 'link','set',pf , 'vf', vf_index, 'vlan', vlan, 'qos', priority]
        execute(cmd, root_helper='sudo')
        self._config_port_up(dev)
        
    def _config_vlan_priority_hostdev(self, fabric, pf, vf_index, dev, vlan, priority='0'):
        fabric_details = self.rm.get_fabric_details(fabric)
        fabric_type = fabric_details['fabric_type']
        if fabric_type == 'ib':
            self._config_vlan_ib(vlan, fabric_details, dev, vf_index)
        else: 
            cmd = ['ip', 'link','set',pf , 'vf', vf_index, 'vlan', vlan, 'qos', priority]
            execute(cmd, root_helper='sudo')
    
    def _config_vlan_ib(self, vlan, fabric_details, dev, vf_index):
        hca_port = fabric_details['hca_port'] 
        pf_mlx_dev = fabric_details['pf_mlx_dev'] 
        ppkey_idx = self._get_pkey_idx(vlan, pf_mlx_dev, hca_port)
        if ppkey_idx:
            self._config_vf_pkey(ppkey_idx, DEFAULT_PKEY_IDX, pf_mlx_dev, dev, hca_port)
        
    def _get_pkey_idx(self, vlan, pf_mlx_dev, hca_port):
        PKEYS_PATH="/sys/class/infiniband/%s/ports/%s/pkeys/*"
        paths = PKEYS_PATH % (pf_mlx_dev , hca_port)
        for path in glob.glob(paths):
            fd = open(path)
            pkey = fd.readline()
            fd.close()
            if (int(pkey, 0) - int(BASE_PKEY, 0)) == vlan:
                return path.split('/')[-1]
        return None
        
    def _config_port_down(self, dev, vnic_type=constants.VIF_TYPE_DIRECT):
        if vnic_type == constants.VIF_TYPE_DIRECT:
            cmd = ['ip', 'link', 'set', dev, 'down']       
            execute(cmd, root_helper='sudo')
        
    def _config_port_up(self,dev):
        cmd = ['ip', 'link', 'set', dev, 'up']       
        execute(cmd, root_helper='sudo')        

    def _set_devname(self, device_name, dev):
        self._config_port_down(dev)
        cmd = ['ip', 'link', 'set', dev, 'name', device_name]       
        execute(cmd, root_helper='sudo')        

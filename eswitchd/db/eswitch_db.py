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
import logging
from eswitchd.common import constants

LOG = logging.getLogger('eswitchd')

class eSwitchDB():

        def __init__(self):
            self.port_table  = {}
            self.port_policy = {}
            self.acl_table = {}
                           
        def create_port(self, port_name, port_type):
            self.port_table.update({port_name: {'type': port_type,
                                                'vnic': None,
                                                'state': None,
                                                'alias': None,
                                                'device_id':None}})

        def plug_nic(self, port_name):
            self.port_table[port_name]['state'] = constants.VPORT_STATE_ATTACHED
            LOG.debug("port table:",self.port_table)

        def get_ports(self):
            return self.port_table

        def get_port_type(self,dev):
            return self.port_table[dev]['type']
        
        def get_port_state(self, dev):
            return self.port_table[dev]['state']

        def get_attached_vnics(self):
            vnics = {}
            for port in self.port_table.values():
                vnic_mac = port['vnic']
                state   = port['state']
                if vnic_mac and state == constants.VPORT_STATE_ATTACHED:
                    vnics[vnic_mac]={'mac':vnic_mac,
                                     'device_id':self.port_policy[vnic_mac]['device_id']}
            return vnics      
                 
        def get_port_policy(self):
            return self.port_policy
        
        def get_port_table(self):
            return self.port_table
        
        def get_vlan(self, vnic_mac):
            if self.vnic_exists(vnic_mac):
                return self.port_policy[vnic_mac]['vlan']
            return
        
        def get_priority(self, vnic_mac):
            if self.vnic_exists(vnic_mac):
                return self.port_policy[vnic_mac]['priority']
            return
        
        def create_vnic(self, vnic_mac):
            if not self.vnic_exists(vnic_mac):
                self.port_policy.update({vnic_mac: {'vlan':None,'dev':None,
                                                    'device_id':None,
                                                    'port_id':None,
                                                    'flow_ids':set([])}})
            
        def get_dev_type(self, dev):
            dev_type = None

            if dev in self.port_table:
                dev_type = self.port_table[dev]['type']
            return dev_type
        
        def get_dev_alias_for_vnic(self, vnic_mac):
            alias = None
            dev = self.get_dev_for_vnic(vnic_mac)
            if dev:
                alias = self.port_table[dev].get('alias')
            return alias
            
        def get_dev_type_for_vnic(self, vnic_mac):
            dev = None

            if vnic_mac in self.port_policy:
                if 'dev' in self.port_policy[vnic_mac]:
                    dev = self.port_policy[vnic_mac]['dev']
            if dev:                     
                return self.port_table[dev]['type']
            else:
                return None
                        
            if vnic_mac in self.port_policy:
                if 'dev' in self.port_policy[vnic_mac]:
                    dev = self.port_policy[vnic_mac]['dev']
            return dev
        
        def get_dev_for_vnic(self, vnic_mac):
            dev = None
            if vnic_mac in self.port_policy:
                if 'dev' in self.port_policy[vnic_mac]:
                    dev = self.port_policy[vnic_mac]['dev']
            return dev
        
        def get_vnic_state(self, vnic_mac):
            dev_state = None
            dev = self.get_dev_for_vnic(vnic_mac)
            if dev:
                dev_state = self.get_port_state(dev)
            return dev_state
                
        def vnic_exists(self, vnic_mac):
            if vnic_mac in self.port_policy:
                return True
            else:
                return False

            
        def attach_vnic(self,port_name, device_id, vnic_mac,dev_name = None):
            self.port_table[port_name]['vnic'] = vnic_mac
            self.port_table[port_name]['alias'] = dev_name
            self.port_table[port_name]['state'] = constants.VPORT_STATE_PENDING
            self.port_table[port_name]['device_id'] = device_id
            dev = self.get_dev_for_vnic(vnic_mac)
            if not dev and vnic_mac != constants.INVALID_MAC:
                if vnic_mac in self.port_policy:
                    vnic_mac_entry = self.port_policy[vnic_mac]
                    vnic_mac_entry['dev'] = port_name 
                    vnic_mac_entry['device_id'] = device_id
                    vnic_mac_entry.setdefault('vlan', None)
                    vnic_mac_entry.setdefault('priority', 0)
                    vnic_mac_entry.setdefault('flow_ids', set([]))
                else:    
                    self.port_policy.update({vnic_mac: {'vlan':None,
                                                        'dev':port_name,
                                                        'device_id':device_id,
                                                        'flow_ids':set([]),
                                                        'priority': 0,
                                                        }})
                return True
            return False
                        
        def detach_vnic(self, vnic_mac):
            dev = self.get_dev_for_vnic(vnic_mac)
            if dev:
                for attr in ['vnic_mac','device_id']:
                    self.port_policy[vnic_mac][attr] = None
                self.port_table[dev]['vnic'] = None
                self.port_table[dev]['alias'] = None
                self.port_table[dev]['state'] = constants.VPORT_STATE_UNPLUGGED
                self.port_table[dev]['device_id'] = None
            return dev
        
        def port_release(self, vnic_mac):
            try:
                dev = self.get_dev_for_vnic(vnic_mac)
                self.port_table[dev]['state'] = None
                vnic = self.port_policy.pop(vnic_mac)
                vnic['type'] = self.port_table[vnic['dev']]['type']
                return vnic
            except KeyError:
                return 
            except IndexError:
                return
            
        def set_vlan(self, vnic_mac, vlan):
            if not self.vnic_exists(vnic_mac):
                self.create_vnic(vnic_mac)

            self.port_policy[vnic_mac]['vlan']=vlan
            
        def set_priority(self, vnic_mac, priority):
            if not self.vnic_exists(vnic_mac):
                self.create_vnic(vnic_mac)

            self.port_policy[vnic_mac]['priority'] = priority            
            
        def set_acl_rule(self, vnic_mac, acl_rule, flow_id):
            if not self.vnic_exists(vnic_mac):
                self.create_vnic(vnic_mac)
            self.acl_table[flow_id] = {'vnic_mac':vnic_mac, 'acl_rule':acl_rule, 'loc':flow_id}
            self.port_policy[vnic_mac]['flow_ids'].add(flow_id)
             
        def update_acl_rule_ref(self, flow_id,acl_ref):
            self.acl_table[flow_id]['loc'] = acl_ref
            
        def del_acl_rule(self, flow_id):        
            if flow_id in self.acl_table:
                vnic_mac = self.acl_table[flow_id]['vnic_mac']
                loc      = self.acl_table[flow_id]['loc']
                self.port_policy[vnic_mac]['flow_ids'].remove(flow_id)
                del self.acl_table[flow_id]
                return (loc, vnic_mac)
            else:  
                return (constants.FLOW_ID_NOT_EXISTS, None)
             
        def update_flow_id(self, old_flow_id, new_flow_id):
            if old_flow_id in self.acl_table:
                self.acl_table[new_flow_id] = self.acl_table[old_flow_id].copy()
                del self.acl_table[old_flow_id]
                vnic_mac = self.acl_table[new_flow_id]['vnic_mac']
                self.port_policy[vnic_mac]['flow_ids'].remove(old_flow_id)
                self.port_policy[vnic_mac]['flow_ids'].add(new_flow_id)
                
        def get_acls_for_vnic(self, vnic_mac):
            acls = []
            if self.vnic_exists(vnic_mac):
                flow_ids = self.port_policy[vnic_mac]['flow_ids']
                for flow_id in flow_ids:
                    acl_rule = self.acl_table[flow_id]['acl_rule']
                    ref      = self.acl_table[flow_id]['loc']
                    acls.append([acl_rule, ref])
            return acls                                    
                

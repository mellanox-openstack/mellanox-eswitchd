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

from oslo_log import log as logging
from eswitchd.common import constants

LOG = logging.getLogger(__name__)


class eSwitchDB():

        def __init__(self):
            self.port_table  = {}
            self.port_policy = {}
                           
        def create_port(self, port_name, port_type):
            self.port_table.update({port_name: {'type': port_type,
                                                'vnic': None,
                                                'state': None,
                                                'alias': None,
                                                'device_id':None}})

        def plug_nic(self, port_name):
            self.port_table[port_name]['state'] = constants.VPORT_STATE_ATTACHED
            LOG.info("port table:",self.port_table)

        def get_ports(self):
            return self.port_table

        def get_port_type(self,dev):
            return self.port_table[dev]['type']
        
        def get_port_state(self, dev):
            state = None
            dev = self.port_table.get(dev)
            if dev:
                state = dev.get('state')
            return state

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
        
        def get_port_policy_matrix(self):
            table_matrix = [ ['VNIC_MAC','VLAN','PRIORITY','DEV','DEVICE_ID']]
            for vnic_mac, port_policy in self.port_policy.items():
                table_matrix.append([vnic_mac,port_policy['vlan'], port_policy['priority'], port_policy['dev'],port_policy['device_id']])
            return table_matrix
        
        def get_port_table(self):
            return self.port_table
        
        def get_port_table_matrix(self):
            table_matrix = [ ['PORT_NAME','TYPE','VNIC','STATE','ALIAS','DEVICE_ID']]
            for port_name, port_data in self.port_table.items():
                table_matrix.append([port_name,port_data['type'], port_data['vnic'],port_data['state'],port_data['alias'],port_data['device_id']])
            return table_matrix
        
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
                                                    'priority':None}})
            
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
                else:    
                    self.port_policy.update({vnic_mac: {'vlan':None,
                                                        'dev':port_name,
                                                        'device_id':device_id,
                                                        'priority': 0,
                                                        }})
                return True
            return False
                        
        def detach_vnic(self, vnic_mac):
            dev = self.get_dev_for_vnic(vnic_mac)
            if dev:
                self.port_table[dev]['vnic'] = None
                self.port_table[dev]['alias'] = None
                self.port_table[dev]['state'] = constants.VPORT_STATE_UNPLUGGED
                self.port_table[dev]['device_id'] = None
            return dev
        
        def port_release(self, vnic_mac):
            try:
                dev = self.get_dev_for_vnic(vnic_mac)
                vnic = self.port_policy.pop(vnic_mac)
                self.port_table[dev]['state'] = None
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

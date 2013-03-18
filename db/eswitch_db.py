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
from common import constants

LOG = logging.getLogger('mlnx_daemon')

class eSwitchDB():

        def __init__(self):
            self.port_table  = {}
            self.port_policy = {}
                           
        def create_port(self, port_name, port_type):
            self.port_table.update({port_name: {'type':port_type,
                                                'vnic':None,
                                                'state':None}})

        def plug_nic(self, port_name):
            self.port_table[port_name]['state'] = constants.VPORT_STATE_ATTACHED

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
        
        def create_vnic(self, vnic_mac):
            if not self.vnic_exists(vnic_mac):
                self.port_policy.update({vnic_mac: {'vlan':None,'dev':None,'device_id':None,'port_id':None}})
            
        def get_dev_type(self, dev):
            dev_type = None

            if dev in self.port_table:
                dev_type = self.port_table[dev]['type']
            return dev_type
        
        def get_dev_type_for_vnic(self, vnic_mac):
            dev = None

            if vnic_mac in self.port_policy:
                if 'dev' in self.port_policy[vnic_mac]:
                    dev = self.port_policy[vnic_mac]['dev']
            if dev:                     
                return self.port_table[dev]['type']
            else:
                return None
         
        def get_dev_for_vnic(self, vnic_mac):
            dev = None
            if vnic_mac in self.port_policy:
                if 'dev' in self.port_policy[vnic_mac]:
                    dev = self.port_policy[vnic_mac]['dev']
            return dev

        def vnic_exists(self, vnic_mac):
            if vnic_mac in self.port_policy:
                return True
            else:
                return False
            
        def attach_vnic(self,port_name, device_id, vnic_mac):
            self.port_table[port_name]['vnic'] = vnic_mac
            self.port_table[port_name]['state'] = constants.VPORT_STATE_PENDING
            dev = self.get_dev_for_vnic(vnic_mac)
            if not dev:
                self.port_policy.update({vnic_mac: {'vlan':None,
                                                    'dev':port_name,
                                                    'device_id':device_id,
                                                     }})
                return True
            return False
                        
        def detach_vnic(self, vnic_mac):
            dev = self.get_dev_for_vnic(vnic_mac)
            if dev:
                for attr in ['vnic_mac','device_id']:
                    self.port_policy[vnic_mac][attr] = None
                self.port_table[dev]['vnic'] = None
                self.port_table[dev]['state'] = constants.VPORT_STATE_UNPLUGGED
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

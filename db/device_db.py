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

LOG = logging.getLogger('mlnx_daemon')

class DeviceDB():
    def __init__(self):
            self.device_db  = {}
            
    def get_pf(self,fabric):
        return self.device_db[fabric]['pf']
    
    def add_fabric(self,fabric,pf,pci_id,hca_port):  
        list_keys = ['vfs','eths','free_vfs','reserved_vfs','free_eths','reserved_eths']  
        details = {}
        for key in list_keys:
            details[key]=[]
        details['pf'] = pf 
        details['pci_id'] = pci_id
        details['hca_port'] = hca_port          
        self.device_db[fabric] = details
        
    def set_fabric_devices(self,fabric,eths,vfs):
        self.device_db[fabric]['vfs'] = vfs
        self.device_db[fabric]['free_vfs'] = vfs[:]
        self.device_db[fabric]['eths'] = eths
        self.device_db[fabric]['free_eths'] = eths[:]
        
    def get_free_eths(self, fabric):
        return self.device_db[fabric]['free_eths']
    
    def get_free_vfs(self,fabric):
        return self.device_db[fabric]['free_vfs']
    
    def get_free_devices(self,fabric):
        return self.device_db[fabric]['free_vfs'] + self.device_db[fabric]['free_eths']
    
    def get_dev_fabric(self,dev):
        for fabric in self.device_db:
            if dev in self.device_db[fabric]['vfs']+self.device_db[fabric]['eths']:
                return fabric
            
    def allocate_device(self,fabric,is_device=True,dev=None):
        available_resources = self.device_db[fabric]['free_vfs']
        if is_device:
            available_resources = self.device_db[fabric]['free_eths']
        try:
            if dev:
                available_resources.remove(dev)
            else:
                dev = available_resources.pop()
            return dev
        except Exception, e:
            LOG.error("exception on device allocation on dev  %s",dev)
            raise e
        
    def deallocate_device(self,fabric,is_device,dev):
        resources = self.device_db[fabric]['vfs']
        available_resources = self.device_db[fabric]['free_vfs']
        if is_device:
            resources = self.device_db[fabric]['eths']
            available_resources = self.device_db[fabric]['free_eths']
        if dev in resources:                          
            available_resources.append(dev)
            return dev          
        else:
            return None
        
 
        

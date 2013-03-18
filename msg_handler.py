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

class BasicMessageHandler(object):
    MSG_ATTRS_VALID_MAP = set()
    def __init__(self, msg):
        self.msg = msg
        
    def execute(self):
        raise Exception("execute method MUST be implemented!")
    
    def validate(self):
        ret = False
        if set(self.msg.keys()) >= self.MSG_ATTRS_VALID_MAP:
            ret = True
        if 'vnic_type' in self.msg.keys():
            ret = self.validate_vnic_type(self.msg['vnic_type'])
        return ret
    
    def validate_vnic_type(self,vnic_type):
        if vnic_type in (constants.VIF_TYPE_DIRECT, constants.VIF_TYPE_HOSTDEV):
            return True
        return False
    
    def build_response(self,status,reason=None, response=None):
        if status:
            msg = {'status':'OK','response':response}
        else:
            msg = {'status':'FAIL','reason':reason}
        return msg 
                          
class AttachVnic(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','vnic_type','device_id','vnic_mac'])
    
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):    
        fabric     = self.msg['fabric']
        vnic_type  = self.msg['vnic_type']
        device_id  = self.msg['device_id']
        vnic_mac   = (self.msg['vnic_mac']).lower() 
        dev = eSwitchHandler.create_port(fabric, vnic_type, device_id, vnic_mac)
        if dev:
            return self.build_response(True, response= {'dev':dev})
        else:
            return self.build_response(False, reason = 'Attach vnic failed')
        
class PlugVnic(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','device_id','vnic_mac'])
    
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):    
        fabric     = self.msg['fabric']
        device_id  = self.msg['device_id']
        vnic_mac   = (self.msg['vnic_mac']).lower() 
        dev = eSwitchHandler.plug_nic(fabric, device_id, vnic_mac)
        if dev:
            return self.build_response(True, response= {'dev':dev})
        else:
            return self.build_response(False, reason = 'Plug vnic failed')
              
class DetachVnic(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','vnic_mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)
        
    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        vnic_mac   = (self.msg['vnic_mac']).lower()
        dev = eSwitchHandler.delete_port(fabric, vnic_mac)
        if dev:
            return self.build_response(True, response = {'dev':dev})
        else:
            return self.build_response(False, reason = 'Detach vnic failed')
        
class SetVLAN(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','port_mac','vlan'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)
        
    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        vnic_mac   = (self.msg['port_mac']).lower()
        vlan   = self.msg['vlan']
        ret = eSwitchHandler.set_vlan(fabric, vnic_mac, vlan)
        reason = None
        if not ret:
            reason ='Set VLAN Failed'
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response = {})
        

class GetVnics(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)
        
    def execute(self, eSwitchHandler):
        fabric   = self.msg['fabric']
        if fabric == '*':
            fabrics = eSwitchHandler.eswitches.keys()
            LOG.debug("fabrics =%s",fabrics)
        else:
            fabrics = [fabric]
        vnics = eSwitchHandler.get_vnics(fabrics)
        return self.build_response(True, response =vnics)

class PortRelease(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','ref_by','mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)
        
    def execute(self, eSwitchHandler):
        ref_by_keys = ['mac_address']
        fabric     = self.msg['fabric']
        vnic_mac   = (self.msg['mac']).lower()
        ref_by     = self.msg['ref_by']
        
        reason = None
        if ref_by not in ref_by_keys:
            reason = "reb_by %s is not supported" % ref_by
        else:
            ret = eSwitchHandler.port_release(fabric, vnic_mac)
            if not ret:
                reason = "port release failed"
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response = {})
           
class SetFabricMapping(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','interface'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        interface   = self.msg['interface']
        return self.build_response(True, response = {'fabric':fabric,'dev':interface})
# @todo: add support for dynamic fabric setting
#        (fabric,dev) = eSwitchHandler.set_fabric_mapping(fabric, interface)
#        if not dev:
#            return self.build_response(False, reason ='Set Fabric Mapping Failed')
#        if dev != interface:
#            return self.build_response(False, reason ='Fabric configured with interface %s'% dev)
#        return self.build_response(True, response = {'fabric':fabric,'dev':dev})

class PortUp(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','ref_by','mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        ref_by   = self.msg['ref_by']
        mac   = self.msg['mac']
        return self.build_response(True, response = {})

class PortDown(BasicMessageHandler):
    MSG_ATTRS_VALID_MAP = set(['fabric','ref_by','mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        ref_by   = self.msg['ref_by']
        mac   = self.msg['mac']
        return self.build_response(True, response = {})
       
class MessageDispatch(object):
    MSG_MAP = {
               'create_port': AttachVnic,
               'delete_port':DetachVnic,
               'set_vlan':SetVLAN,
               'get_vnics':GetVnics,
               'port_release':PortRelease,
               'port_up':PortUp,
               'port_down':PortDown,
               'define_fabric_mapping':SetFabricMapping,
               'plug_nic':PlugVnic,
               }
    def __init__(self,eSwitchHandler):
        self.eSwitchHandler = eSwitchHandler
    
    def handle_msg(self, msg):
        LOG.debug("Handling message - %s",msg)
        result = {}
        action = msg.pop('action')
        
        if action in MessageDispatch.MSG_MAP.keys():
            msg_handler = MessageDispatch.MSG_MAP[action](msg)
            if msg_handler.validate():
                result = msg_handler.execute(self.eSwitchHandler)
            else:
                LOG.error('Invalid message - cannot handle')
                result = {'status':'FAIL','reason':'validation failed'}
        else:
            LOG.error("Unsupported action - %s",action)
            result = {'action':action, 'status':'FAIL','reason':'unknown action'}           
        result['action'] = action    
        return result    
    

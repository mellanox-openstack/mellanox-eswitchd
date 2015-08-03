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
from common import constants
from db.eswitch_db import eSwitchDB
from eswitch_handler import eSwitchHandler

LOG = logging.getLogger('eswitchd')


class BasicMessageHandler(object):
    MSG_ATTRS_MANDATORY_MAP = set()
    def __init__(self, msg):
        self.msg = msg

    def execute(self):
        raise Exception("execute method MUST be implemented!")

    def validate(self):
        ret = False
        if set(self.msg.keys()) >= self.MSG_ATTRS_MANDATORY_MAP:
            ret = True
        if 'vnic_type' in self.msg.keys():
            ret = self.validate_vnic_type(self.msg['vnic_type'])
        return ret

    def validate_vnic_type(self,vnic_type):
        if vnic_type in (constants.VIF_TYPE_DIRECT, constants.VIF_TYPE_HOSTDEV, constants.VIF_TYPE_MLNX_DIRECT):
            return True
        return False

    def build_response(self,status,reason=None, response=None):
        if status:
            msg = {'status':'OK','response':response}
        else:
            msg = {'status':'FAIL','reason':reason}
        return msg

class AttachVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric', 'vnic_type',
                                   'device_id', 'vnic_mac',
                                   'dev_name'])

    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        vnic_type  = self.msg['vnic_type']
        device_id  = self.msg['device_id']
        vnic_mac   = (self.msg['vnic_mac']).lower()
        dev_name = self.msg['dev_name']
        dev = eSwitchHandler.create_port(fabric, vnic_type, device_id, vnic_mac, dev_name)
        if dev:
            return self.build_response(True, response= {'dev':dev})
        else:
            return self.build_response(False, reason = 'Attach vnic failed')

class PlugVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','device_id',
                                   'vnic_mac','vnic_type',
                                   'dev_name'])

    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        device_id  = self.msg['device_id']
        vnic_mac   = (self.msg['vnic_mac']).lower()
        vnic_type = self.msg['vnic_type']
        dev_name = self.msg['dev_name']

        if vnic_type == constants.VIF_TYPE_MLNX_DIRECT:
            vnic_type = constants.VIF_TYPE_DIRECT
        if vnic_type == constants.VIF_TYPE_DIRECT:
            dev = eSwitchHandler.create_port(fabric, vnic_type,
                                             device_id, vnic_mac,
                                             dev_name)
        dev = eSwitchHandler.plug_nic(fabric, device_id, vnic_mac, dev_name)
        if dev:
            return self.build_response(True, response= {'dev':dev})
        else:
            return self.build_response(False, reason = 'Plug vnic failed')

class DetachVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','vnic_mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        vnic_mac   = (self.msg['vnic_mac']).lower()
        dev = eSwitchHandler.delete_port(fabric, vnic_mac)
        if dev:
            return self.build_response(True, response = {'dev':dev})
        else:
            return self.build_response(True, response = {})

class SetVLAN(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','port_mac','vlan'])
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

class SetPriority(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','port_mac','priority'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        vnic_mac   = (self.msg['port_mac']).lower()
        priority   = self.msg['priority']
        ret = eSwitchHandler.set_priority(fabric, vnic_mac, priority)
        reason = None
        if not ret:
            reason ='Set Priority Failed'
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response = {})

class GetVnics(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric'])
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
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','ref_by','mac'])
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
            try:
                eSwitchHandler.port_release(fabric, vnic_mac)
            except Exception,e:
                reason = "port release failed"
                LOG.exception("PortRelease failed")
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response = {})

class SetFabricMapping(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','interface'])
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
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','ref_by','mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        ref_by   = self.msg['ref_by']
        mac   = self.msg['mac']
        return self.build_response(True, response = {})

class PortDown(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric','ref_by','mac'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric     = self.msg['fabric']
        ref_by   = self.msg['ref_by']
        mac   = self.msg['mac']
        return self.build_response(True, response = {})

class SetAclRule(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric', 'port_mac', 'flow_id',
                               'acl_action'])

    MSG_ATTRS_ALLOWED_MAP = set(['fabric', 'port_mac', 'flow_id','priority',
                                 'src_mac', 'dst-mac', 'src_ipv4', 'tcp_src_port',
                                 'tcp_dst_port','dst_ipv4', 'udp_src_port',
                                 'udp_dst_port', 'acl_action','ip_protocol'])
    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric = self.msg.pop('fabric')
        mac    = self.msg['port_mac'].lower()
        ret = eSwitchHandler.set_acl_rule(fabric, mac, self.msg)

        if not ret:
            reason = 'Set ACL Rule Failed'
            self.build_response(False, reason=reason)
        return self.build_response(True, response = {})

    def validate(self):
        ret = False
        if super(SetAclRule, self).validate():
            if set(self.msg.keys()) <= set(self.MSG_ATTRS_ALLOWED_MAP):
                if 'acl_action' in self.msg.keys():
                    ret = self.validate_acl_action(self.msg['acl_action'])
        return ret

    def validate_acl_action(self, acl_action):
        if acl_action in constants.ACL_ACTIONS:
            return True
        return False

class DeleteAclRule(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric', 'flow_id'])

    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric = self.msg['fabric']
        flow_id = self.msg['flow_id']
        ret = eSwitchHandler.delete_acl_rule(fabric, flow_id)

        reason = None
        if not ret:
            reason ='Delete ACL Failed'
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response = {})

class UpdateFlowId(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric', 'old_flow_id', 'new_flow_id'])

    def __init__(self,msg):
        BasicMessageHandler.__init__(self,msg)

    def execute(self, eSwitchHandler):
        fabric = self.msg['fabric']
        old_flow_id = self.msg['old_flow_id']
        new_flow_id = self.msg['new_flow_id']
        ret = eSwitchHandler.update_flow_id(fabric, old_flow_id, new_flow_id)
        return self.build_response(ret, response = {})

class GetEswitchTables(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric'])

    def __init__(self,msg):
        BasicMessageHandler.__init__(self, msg)

    def execute(self, eSwitchHandler):
        fabric = self.msg.get('fabric', '*')
        if fabric == '*':
            fabrics = eSwitchHandler.eswitches.keys()
            LOG.debug("fabrics =%s",fabrics)
        else:
            fabrics = [fabric]

        return self.build_response(True, response = {'tables':eSwitchHandler.get_eswitch_tables(fabrics)})

class MessageDispatch(object):
    MSG_MAP = {
               'create_port': AttachVnic,
               'delete_port': DetachVnic,
               'set_vlan': SetVLAN,
               'get_vnics': GetVnics,
               'port_release': PortRelease,
               'port_up': PortUp,
               'port_down': PortDown,
               'define_fabric_mapping': SetFabricMapping,
               'plug_nic': PlugVnic,
               'acl_set': SetAclRule,
               'acl_delete': DeleteAclRule,
               'flow_id_update': UpdateFlowId,
               'set_priority': SetPriority,
               'get_eswitch_tables': GetEswitchTables,
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

def main():
    handler = eSwitchHandler([('mlx1','eth4')])
    dispatcher = MessageDispatch(handler)
    mac = '52:54:00:97:3f:1f'
    msg = {
           'src_ipv4': '10.20.30.50',
            'fabric': 'mlx1',
            'dst_ipv4': '11.22.33.44',
            'acl_action': 'forward',
            'port_mac': mac,
            'priority': '32768',
            'udp_src_port': '100',
            'flow_id': 2.0,
            'action': 'acl_set',
            'udp_dst_port': '400',
            'ip_protocol':17}

    dispatcher.handle_msg(msg)

if __name__ == '__main__':
    main()

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

from eswitchd.common import constants
#from nova.openstack.common import log as logging
import logging
from eswitchd.utils.command_utils import execute

LOG = logging.getLogger('eswitchd')

class AclHandler(object):
    def build_acl_rule(self, params):
        """Parse a dictionary of acl rule
           and return new dictionary of acl rule
        """
        proto = None
        flow_id = params.get('flow_id')
        acl_params = {}
        if 'ip_protocol' in params:
            proto = params['ip_protocol']
            
        if proto == constants.PROTOCOLS['tcp4']:
            for param in constants.ACL_TCP_PARAMS_MAP:
                if param in params:
                    acl_params[constants.ACL_TCP_PARAMS_MAP[param]] = params[param]
                    acl_params['flow-type'] = 'tcp4'
                    
        elif proto == constants.PROTOCOLS['udp4']:
            for param in constants.ACL_UDP_PARAMS_MAP:
                if param in params:
                    acl_params[constants.ACL_UDP_PARAMS_MAP[param]] = params[param]
                    acl_params['flow-type'] = 'udp4'
        elif not proto:
            acl_params['flow-type'] = constants.DEFAULT_FLOW_TYPE      
        else:
            return (None, None)
        for param in params:
            if param in constants.ACL_PARAMS_MAP:
                acl_params[constants.ACL_PARAMS_MAP[param]] = params[param]
        acl_params['dst-mac'] = params['port_mac']
        return (flow_id, acl_params)
    
    def set_acl_rule(self, pf, acl_rule):
        """ Configure the ACL rule in HCA"""
        raise Exception("set_acl_rule method MUST be implemented!")
    
    def del_acl_rule(self, pf, ref):
        """ Delete ACL rule from HCA"""
        raise Exception("del_acl_rule method MUST be implemented!")
    
    def set_acl_rules(self, pf ,acl_rules):
        for (acl_rule, ref) in  acl_rules:
            self.set_acl_rule(pf, acl_rule)
    
class EthtoolAclHandler(AclHandler):  
    def set_acl_rule(self, pf, acl_rule, ref=None):
        ethtool_cmd = ['ethtool', '-U', pf]
        
        if ref:
            acl_rule['loc'] = ref
        else: 
            acl_rule['loc'] = acl_rule['flow_id']
                   
        for acl_param in constants.ETHTOOL_ACL_PARAMS:
            if acl_param in acl_rule:
                if acl_param == 'action':
                    acl_val = constants.ETHTOOL_ACL_ACTIONS[acl_rule[acl_param]]
                elif acl_param == 'loc':
                    acl_val = '%.f'%(acl_rule['flow_id'])
                else:
                    acl_val = acl_rule[acl_param]
                if acl_val:    
                    ethtool_cmd = ethtool_cmd + [acl_param, acl_val]
                
        execute(ethtool_cmd, root_helper=None)
        return (acl_rule['loc']) 
    
    def del_acl_rule(self, pf, ref):
        loc = '%.0f'%(ref)
        cmd = ['ethtool', '-U', pf ,'delete', loc]
        execute(cmd, root_helper=None)

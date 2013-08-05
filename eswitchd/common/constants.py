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

VENDOR='0x15b3'
SUBS_DEV='0x0050'
LINK_UP='1'


VIF_TYPE_MLNX_DIRECT = 'mlnx_direct'
VIF_TYPE_DIRECT = 'direct'
VIF_TYPE_HOSTDEV = 'hostdev'

VPORT_STATE_ATTACHED = 'attached'
VPORT_STATE_PENDING = 'pending'
VPORT_STATE_UNPLUGGED = 'unplugged'

UNTAGGED_VLAN_ID = 4095

ACL_PARAMS_MAP = {'src_mac':'src', 'dst-mac':'dst-mac', 'flow_id':'flow_id',
                  'src_ipv4':'src-ip', 'dst_ipv4': 'dst-ip','acl_action':'action',
                  'priority':'priority','flow_type':'flow-type'
                  }
ACL_TCP_PARAMS_MAP = {'tcp_src_port':'src-port', 'tcp_dst_port':'dst-port'}

ACL_UDP_PARAMS_MAP = {'udp_src_port':'src-port', 'udp_dst_port':'dst-port'}

ACL_ACTIONS = {'drop':'-1', 'forward':'0'}

ETHTOOL_ACL_ACTIONS = {'drop':'-1', 'forward':'0'}

PROTOCOLS = {'tcp4':6, 'udp4':17}

ETHTOOL_ACL_PARAMS = ['flow-type', 'proto', 'src-ip', 'dst-ip', 'src-port',
                      'dst-port', 'dst-mac', 'action','loc']

DEFAULT_FLOW_TYPE = 'ip4'

FLOW_ID_NOT_EXISTS = None

INVALID_MAC = '00:00:00:00:00:00'

ADMIN_GUID_PATH = "/sys/class/infiniband/%s/iov/ports/%s/admin_guids/%s"

INVALID_GUID = 'ffffffffffffffff'


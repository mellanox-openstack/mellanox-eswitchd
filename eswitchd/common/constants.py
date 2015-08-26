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
VIF_TYPE_HOSTDEV = 'ib_hostdev'


VPORT_STATE_ATTACHED = 'attached'
VPORT_STATE_PENDING = 'pending'
VPORT_STATE_UNPLUGGED = 'unplugged'

UNTAGGED_VLAN_ID = 4095

INVALID_MAC = '00:00:00:00:00:00'

ADMIN_GUID_PATH = "/sys/class/infiniband/%s/iov/ports/%s/admin_guids/%s"

INVALID_GUID = 'ffffffffffffffff'

IFCS_PATH = '/sys/class/net/*'

CONN_URL = '%(transport)s://%(addr)s:%(port)s'
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

from oslo.config import cfg

DEFAULT_INTERFACE_MAPPINGS = []

mlx_daemon_opts = [
                    cfg.StrOpt('socket_vif', default="tcp://0.0.0.0:5001"),
                    cfg.StrOpt('socket_of', default="tcp://0.0.0.0:5000"),
                    cfg.ListOpt('fabrics',
                                default=DEFAULT_INTERFACE_MAPPINGS,
                                help=("List of <physical_network>:<physical_interface>")),
                    cfg.IntOpt('default_timeout',
                               default=5000,
                               help=('Default timeout waiting for messages')),
                    cfg.IntOpt('max_polling_count',
                               default=5,
                               help=('Daemon will do sync after max_polling_count * default_timeout'))

]
cfg.CONF.register_opts(mlx_daemon_opts, "DAEMON")

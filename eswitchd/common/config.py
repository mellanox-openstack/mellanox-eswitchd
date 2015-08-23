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

from oslo_config import cfg


LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR')
default_opts = [cfg.StrOpt('log_file',
                           default='/var/log/eswitchd/eswitchd.log',
                           help='Full path to log file'),
                cfg.StrOpt('log_level',
                           choices=LOG_LEVELS,
                           default='DEBUG',
                           help='Valid values: %s' % str(LOG_LEVELS)),
                cfg.StrOpt('log_format',
                           default=('%(asctime)s %(levelname)s '
                                    '%(name)s [-] %(message)s'),
                           help=('logging format, as supported by the python '
                                 'logging module.'))]

DEFAULT_INTERFACE_MAPPINGS = []
mlx_daemon_opts = [
                    cfg.StrOpt('socket_os_transport', default="tcp"),
                    cfg.StrOpt('socket_os_port', default="60001"),
                    cfg.StrOpt('socket_os_addr', default="0.0.0.0"),
                    cfg.ListOpt('fabrics',
                                default=DEFAULT_INTERFACE_MAPPINGS,
                                help=("List of <physical_network>:<physical_interface>")),
                    cfg.IntOpt('default_timeout',
                               default=5000,
                               help=('Default timeout waiting for messages')),
                    cfg.IntOpt('max_polling_count',
                               default=5,
                               help=('Daemon will do sync after max_polling_count * default_timeout')),
                    cfg.StrOpt('rootwrap_conf',
                               default='/etc/eswitchd/rootwrap.conf',
                               help=('eswitchd rootwrap configuration file'))
]

eswitch_opts = [
    cfg.ListOpt('physical_interface_mappings',
                help=("List of <physical_network>:<physical_interface>"))
]


cfg.CONF.register_opts(default_opts, "DEFAULT")
cfg.CONF.register_opts(mlx_daemon_opts, "DAEMON")
cfg.CONF.register_opts(eswitch_opts, "ESWITCH")

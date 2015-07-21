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

import logging
from oslo_config import cfg
from common import config
from utils.command_utils import execute,execute_bg
from utils import pci_utils

#/usr/local/bin/lri -v -c 127.0.0.1:6633 -p 127.0.0.1 -f default -m 0002c9397331

LOG = logging.getLogger('eswitchd')

OF_LOG = '/var/log/eswitchd/of-dpid.log'
OF_CMD = '/usr/local/bin/lri'
DAEMON_IP = '127.0.0.1'

class OfHandler(object):
    def __init__(self,fabrics=None):
        self._parse_config()
        self.putils = pci_utils.pciUtils()

    def _parse_config(self):
        self.of_fabrics = {}
        fabrics_config = cfg.CONF.OF.of_agent_mappings
        self.socket_of_port = cfg.CONF.DAEMON.socket_of_port

        if fabrics_config:
            for entry in fabrics_config:
                if ':' in entry:
                    try:
                        fabric, controller, dpid = entry.split(':')
                        self.of_fabrics[fabric] = {'controller':controller,
                                                   'dpid':dpid}
                    except ValueError as ex:
                        LOG.error("Error parsing OF Agent Mapping")
                else:
                    LOG.error("Cannot parse OF Agent Mappings")
 
        self.daemon_ip = DAEMON_IP

    def _get_dpid(self, pf, fabric_type):
       if pf == 'auto':
           pf = self.putils.get_pf(fabric_type)
       mac = self.putils.get_eth_mac(pf)
       return mac.replace(":","")

    def _run_of_agents(self, fabrics):
        for (fabric, pf, fabric_type) in fabrics:
            try:
                controller = self.of_fabrics[fabric]['controller']
                dpid = self.of_fabrics[fabric]['dpid']
                if dpid == 'auto':
                    dpid = self._get_dpid(pf, fabric_type)
                cmd = [OF_CMD, '-v', '-c', controller, '-p', "%s:%s" % (self.daemon_ip, self.socket_of_port), '-f', fabric, '-m', dpid]
                of_log_file = OF_LOG.replace('dpid', dpid)
                log = open(of_log_file, 'a')
                execute_bg(cmd, log=log)
            except:
                LOG.error("Problem with running OF Agent for fabric %s",fabric)

    def add_fabrics(self, fabrics):
        self._run_of_agents(fabrics)

if __name__ == '__main__':
    handler = OfHandler(fabrics=['mlx1'])
    handler.run_of_agents()

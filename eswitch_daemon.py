#!/usr/bin/env python
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

import json
import sys
import zmq
from oslo.config import cfg
from nova.openstack.common import log as logging
from common import config
import msg_handler as message
from eswitch_handler import eSwitchHandler

LOG = logging.getLogger('mlnx_daemon')
   
class MlxEswitchDaemon(object):   
    def __init__(self):
        self.max_polling_count = cfg.CONF.DAEMON.max_polling_count
        self.default_timeout = cfg.CONF.DAEMON.default_timeout
        fabrics = self._parse_physical_mapping()
        self.eswitch_handler = eSwitchHandler(fabrics)
        self.dispatcher = message.MessageDispatch(self.eswitch_handler)
       
    def start(self):  
        self._init_connections()

    def _parse_physical_mapping(self):
        fabrics = []
        for entry in cfg.CONF.DAEMON.fabrics:
            if ':' in entry:
                try:
                    fabric,pf = entry.split(':')
                    fabrics.append((fabric,pf))
                except ValueError as ex:
                    LOG.error(_("Invalid fabric: "
                                "'%(entry)s' - ",
                                "Service terminated!"),
                              locals())
                    raise
            else:
                LOG.error("Cannot parse Fabric Mappings")
                raise Exception("Cannot parse Fabric Mappings")
        return fabrics
        
    def _init_connections(self):
        context = zmq.Context()
        self.socket_of  = context.socket(zmq.REP)
        self.socket_vif = context.socket(zmq.REP)
        self.socket_of.bind(cfg.CONF.DAEMON.socket_of)
        self.socket_vif.bind(cfg.CONF.DAEMON.socket_vif)
        self.poller = zmq.Poller()
        self.poller.register(self.socket_of, zmq.POLLIN)
        self.poller.register(self.socket_vif, zmq.POLLIN)
        
    def _handle_msg(self):
        data = None
        conn = dict(self.poller.poll(self.default_timeout))
        if conn:
            if conn.get(self.socket_of) == zmq.POLLIN:
                msg = self.socket_of.recv()
                sender = self.socket_of
            elif conn.get(self.socket_vif) == zmq.POLLIN:
                msg = self.socket_vif.recv()
                sender = self.socket_vif
            if msg:
                data = json.loads(msg)
            
        if data:
            result = self.dispatcher.handle_msg(data)     
            msg = json.dumps(result)
            sender.send(msg)
        
    def daemon_loop(self):
        LOG.info("Daemon Started!")
        polling_counter = 0
        while True:
            try:
                self._handle_msg()
            except Exception,e:
                LOG.error("exception during message handling - %s",e)
            if polling_counter == self.max_polling_count:
                LOG.debug("Resync devices")
            #    self.eswitch_handler.sync_devices()
                polling_counter = 0
            else:
                polling_counter+=1
            
def main():
    cfg.CONF(project='mlnx_daemon')
    logging.setup('mlnx_daemon')
    try:
        daemon = MlxEswitchDaemon()
        daemon.start()
    except Exception,e:
        LOG.error("Failed to start EswitchDaemon - Daemon terminated! %s",e)
        sys.exit(1)
        
    daemon.daemon_loop()
          
if __name__ == '__main__':
    main()

    

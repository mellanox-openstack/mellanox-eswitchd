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
import logging
from common import config
from eswitch_handler import eSwitchHandler
from utils.helper_utils import set_conn_url
import msg_handler as message


cfg.CONF(project='eswitchd')

logging.basicConfig(filename=cfg.CONF.DEFAULT.log_file,
                    filemode='w',
                    format=cfg.CONF.DEFAULT.log_format,
                    level=logging.getLevelName(cfg.CONF.DEFAULT.log_level))

LOG = logging.getLogger('eswitchd')


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
        if cfg.CONF.ESWITCH.physical_interface_mappings:
            fabrics_config = cfg.CONF.ESWITCH.physical_interface_mappings
        else:
            fabrics_config = cfg.CONF.DAEMON.fabrics

        for entry in fabrics_config:
            if ':' in entry:
                try:
                    fabric, pf = entry.split(':')
                    fabrics.append((fabric, pf))
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
        self.socket_os = context.socket(zmq.REP)
        of_transport = cfg.CONF.DAEMON.socket_of_transport
        of_port = cfg.CONF.DAEMON.socket_of_port
        of_addr = cfg.CONF.DAEMON.socket_of_addr
        os_transport = cfg.CONF.DAEMON.socket_os_transport
        os_port = cfg.CONF.DAEMON.socket_os_port
        os_addr = cfg.CONF.DAEMON.socket_os_addr
        self.conn_of_url = set_conn_url(of_transport, of_addr, of_port)
        self.conn_os_url = set_conn_url(os_transport, os_addr, os_port)

        self.socket_of.bind(self.conn_of_url)
        self.socket_os.bind(self.conn_os_url)
        self.poller = zmq.Poller()
        self.poller.register(self.socket_of, zmq.POLLIN)
        self.poller.register(self.socket_os, zmq.POLLIN)

    def _handle_msg(self):
        data = None
        conn = dict(self.poller.poll(self.default_timeout))
        if conn:
            if conn.get(self.socket_of) == zmq.POLLIN:
                msg = self.socket_of.recv()
                sender = self.socket_of
            elif conn.get(self.socket_os) == zmq.POLLIN:
                msg = self.socket_os.recv()
                sender = self.socket_os
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
    try:
        daemon = MlxEswitchDaemon()
        daemon.start()
    except Exception,e:
        LOG.exception("Failed to start EswitchDaemon - Daemon terminated! %s",e)
        sys.exit(1)

    daemon.daemon_loop()

if __name__ == '__main__':
    main()



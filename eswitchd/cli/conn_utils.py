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
from oslo.config import cfg
import zmq
import logging
from eswitchd.cli import exceptions
from eswitchd.common import config, constants
from eswitchd.utils.helper_utils import set_conn_url

REQUEST_TIMEOUT = 5000
LOG = logging.getLogger(__name__)


class ConnUtil(object):
    def __init__(self):
        self.__conn = None

        transport = cfg.CONF.DAEMON.socket_os_transport
        port = cfg.CONF.DAEMON.socket_os_port
        addr = cfg.CONF.DAEMON.socket_os_addr
        self.conn_url = set_conn_url(transport, addr, port)

    def send_msg(self,msg):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(self.conn_url)

        try:
            socket.send(msg)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            conn = dict(poller.poll(REQUEST_TIMEOUT))
            if conn:
                if conn.get(socket) == zmq.POLLIN:
                    response_msg = socket.recv(zmq.NOBLOCK)
                    response = self.parse_response_msg(response_msg)
                    return response
            else:
               print 'no result received'
        finally:
            socket.close()
            context.term()

    def parse_response_msg(self, recv_msg):
        msg = json.loads(recv_msg)
        error_msg = " "
        if msg['status'] == 'OK':
            if 'response' in msg:
                return msg['response']
            return
        elif msg['status'] == 'FAIL':
            error_msg = "Action  %s failed: %s" %(msg['action'], msg['reason'])
        else:
            error_msg = "Unknown operation status %s" % msg['status']
        LOG.error(error_msg)
        raise exceptions.MlxException(error_msg)

    def allocate_nic(self, vnic_mac, device_id, fabric, vnic_type, dev_name=None):
        msg = json.dumps({'action':'create_port',
                          'vnic_mac':vnic_mac,
                          'device_id':device_id,
                          'fabric':fabric,
                          'vnic_type':vnic_type,
                          'dev_name':dev_name})
        recv_msg = self.send_msg(msg)
        dev = recv_msg['dev']
        return dev

    def plug_nic(self, vnic_mac, device_id, fabric, vif_type, dev_name):
        msg = json.dumps({'action':'plug_nic',
                          'vnic_mac':vnic_mac,
                          'device_id':device_id,
                          'fabric':fabric,
                          'vnic_type':vif_type,
                          'dev_name':dev_name})

        recv_msg = self.send_msg(msg)
        dev = recv_msg['dev']
        return dev


    def deallocate_nic(self, vnic_mac, fabric):
        msg = json.dumps({'action':'delete_port',
                          'fabric':fabric,
                          'vnic_mac':vnic_mac})
        recv_msg = self.send_msg(msg)
        dev = recv_msg['dev']
        return dev

    def get_tables(self, fabric):
        msg = json.dumps({'action':'get_eswitch_tables',
                          'fabric':fabric,
                          })
        recv_msg = self.send_msg(msg)
        tables = recv_msg['tables']
        return tables


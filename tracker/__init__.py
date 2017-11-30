import json
import logging
import socket

import copy
import threading

from halocoin.ntwrk import receive, send, Message
from tracker.util import *

"""
if len(clients) == 2:
    (addr1, c1), (addr2, c2) = clients.items()
    logger.info('server - send client info to: %s', c1.pub)
    send_msg(c1.conn, c2.peer_msg())
    logger.info('server - send client info to: %s', c2.pub)
    send_msg(c2.conn, c1.peer_msg())
    clients.pop(addr1)
    clients.pop(addr2)
"""


class Tracker:
    def __init__(self, host, port):
        self.clients = {}
        self.logger = logging.getLogger()
        try:
            self.clients = json.load(open('clients.json'), 'r')
        except:
            self.clients = {}

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))
        self.s.listen(10)
        self.s.settimeout(1)

    def start(self):
        while True:
            self.listen()

    def listen(self):
        try:
            client_sock, address = self.s.accept()
            threading.Thread(target=self.connection_handle, args=(client_sock, address)).start()
        except Exception as e:
            pass

    def connection_handle(self, client_sock, address):
        response, leftover = receive(client_sock)
        if response.getFlag():
            message = Message.from_yaml(response.getData())
            data = message.get_body()
        else:
            client_sock.close()
            return
        priv_info = copy.deepcopy(data)
        pub_addr_message = {
            "ip": address[0],
            "port": address[1]
        }
        response = Message(headers={'ack': message.get_header('id')},
                           body=pub_addr_message)
        send(response, client_sock)

        response, leftover = receive(client_sock)
        if response.getFlag():
            message = Message.from_yaml(response.getData())
            data = message.get_body()
        else:
            client_sock.close()
            return

        verify = data['ip'] == pub_addr_message['ip'] and data['port'] == pub_addr_message['port'] and \
                 data['node_id'] == priv_info['node_id']

        if verify:
            if priv_info['node_id'] not in self.clients:
                self.clients[priv_info['node_id']] = {
                    "pub_ip": address[0],
                    "pub_port": address[1],
                    "priv_ip": priv_info['ip'],
                    "priv_port": priv_info['port']
                }
                response = Message(headers={'ack': message.get_header('id')},
                                   body=self.clients)
                send(response, client_sock)

        client_sock.close()
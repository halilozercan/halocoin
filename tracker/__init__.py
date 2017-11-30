import json
import logging
import socket
import sys

from halocoin.ntwrk import receive, send
from tracker.util import *

logger = logging.getLogger()
try:
    clients = json.load(open('clients.json'), 'r')
except:
    clients = {}


def main(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(1)
    s.settimeout(30)

    while True:
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue

        logger.info('connection address: %s', addr)
        response, leftover = receive(conn)
        if response.getFlag():
            data = response.getData()
        else:
            conn.close()
            continue
        priv_addr = msg_to_addr(data)
        success = send(addr_to_msg(addr), conn)
        if not success:
            conn.close()
            continue
        response, leftover = receive(conn)
        if response.getFlag():
            data = response.getData()
        else:
            conn.close()
            continue
        data_addr = msg_to_addr(data)
        if data_addr == addr:
            logger.info('client reply matches')
            clients[addr] = Client(conn, addr, priv_addr)
            send(json.dumps(clients), conn)
        else:
            logger.info('client reply did not match')
            conn.close()
            continue

        logger.info('server - received data: %s', data)

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
        conn.close()
import logging
import socket
import sys
import uuid
from threading import Event, Thread

import copy

from halocoin.ntwrk import send, receive, Message, command
from tracker.util import *

logger = logging.getLogger('client')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
STOP = Event()


def accept(port):
    logger.info("accept %s", port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind(('', port))
    s.listen(1)
    s.settimeout(5)
    while not STOP.is_set():
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue
        else:
            logger.info("Accept %s connected!", port)
            # STOP.set()


def connect(local_addr, addr):
    logger.info("connect from %s to %s", local_addr, addr)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind(local_addr)
    while not STOP.is_set():
        try:
            s.connect(addr)
        except socket.error:
            continue
        # except Exception as exc:
        #     logger.exception("unexpected exception encountered")
        #     break
        else:
            logger.info("connected from %s to %s success!", local_addr, addr)
            # STOP.set()


def main(host, port):
    node_id = str(uuid.uuid4())
    sa = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sa.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sa.connect((host, port))
    sa.settimeout(10)
    priv_addr = sa.getsockname()

    priv_info = {
        "ip": priv_addr[0],
        "port": priv_addr[1],
        "node_id": node_id
    }
    pub_info = command((host, port), priv_info, node_id, sock=sa)
    logger.info("client %s %s - received data: %s", priv_addr[0], priv_addr[1], pub_info)
    clients = command((host, port), {
        "ip": pub_info["ip"],
        "port": pub_info["port"],
        "node_id": node_id
    }, node_id, sock=sa)

    logger.info(
        "client public is %s and private is %s",
        clients[node_id]["pub_port"], clients[node_id]["priv_port"],
    )

    """
    threads = {
        '0_accept': Thread(target=accept, args=(priv_addr[1],)),
        '1_accept': Thread(target=accept, args=(client_pub_addr[1],)),
        '2_connect': Thread(target=connect, args=(priv_addr, client_pub_addr,)),
        '3_connect': Thread(target=connect, args=(priv_addr, client_priv_addr,)),
    }
    for name in sorted(threads.keys()):
        logger.info('start thread %s', name)
        threads[name].start()

    while threads:
        keys = list(threads.keys())
        for name in keys:
            try:
                threads[name].join(1)
            except TimeoutError:
                continue
            if not threads[name].is_alive():
                threads.pop(name)
    """


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, message='%(asctime)s %(message)s')
    main(*addr_from_args(sys.argv))

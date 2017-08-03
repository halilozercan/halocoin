"""When a peer talks to us, this is how we generate a response. This is the external API.
"""
import copy
import json
import socket
import sys

import time

import custom
import ntwrk
import tools
from ntwrk import Message
from service import Service, threaded, sync


class PeerListenService(Service):
    def __init__(self, engine):
        Service.__init__(self, 'peer_receive')
        self.engine = engine
        self.db = None
        self.blockchain = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.settimeout(1)
            self.s.bind(('0.0.0.0', self.engine.config['peer.port']))
            self.s.listen(10)
            return True
        except:
            tools.log("Could not start Peer Receive socket!")
            return False

    @threaded
    def listen(self):
        try:
            client_sock, address = self.s.accept()
            response, leftover = ntwrk.receive(client_sock)
            if response.getFlag():
                message = Message.from_yaml(response.getData())
                request = json.loads(message.get_body())
                try:
                    if hasattr(self, request['action']):
                        kwargs = copy.deepcopy(request)
                        del kwargs['action']
                        result = getattr(self, request['action'])(**kwargs)
                    else:
                        result = 'Received action is not valid'
                except:
                    result = 'Something went wrong while evaluating.\n'
                    tools.log(sys.exc_info())
                response = Message(headers={'ack': message.get_header('id')},
                                   body=result)
                ntwrk.send(response, client_sock)
                client_sock.close()
        except:
            pass

    @sync
    def receive_peer(self, peer):
        ps = self.db.get('peers_ranked')
        if peer[0] not in map(lambda x: x[0][0], ps):
            ps = tools.add_peer_ranked(peer, ps)
        self.db.put('peers_ranked', ps)

    @sync
    def block_count(self):
        length = self.db.get('length')
        d = '0'
        if length >= 0:
            d = self.db.get('diffLength')
        return {'length': length, 'diffLength': d}

    @sync
    def range_request(self, range):
        out = []
        counter = 0
        while range[0] + counter <= range[1]:
            block = self.db.get(range[0] + counter)
            if block and 'length' in block:
                out.append(block)
            counter += 1
        return out

    @sync
    def peers(self):
        return self.db.get('peers_ranked')

    @sync
    def txs(self):
        return self.blockchain.tx_pool()

    @sync
    def pushtx(self, tx):
        self.blockchain.tx_queue.put(tx)
        return 'success'

    @sync
    def pushblock(self, blocks):
        self.blockchain.blocks_queue.put(blocks)
        return 'success'

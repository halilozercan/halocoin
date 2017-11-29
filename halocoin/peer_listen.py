import copy
import json
import socket
import sys
import uuid

from halocoin import ntwrk
from halocoin import tools
from halocoin.ntwrk import Message
from halocoin.service import Service, threaded, sync


class PeerListenService(Service):
    def __init__(self, engine):
        Service.__init__(self, 'peer_receive')
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.account = None
        self.node_id = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account

        if not self.db.exists('node_id'):
            self.db.put('node_id', str(uuid.uuid4()))

        self.node_id = self.db.get('node_id')

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.settimeout(1)
            self.s.bind(('0.0.0.0', self.engine.config['port']['peers']))
            self.s.listen(10)
            return True
        except Exception as e:
            tools.log("Could not start Peer Receive socket!")
            return False

    @threaded
    def listen(self):
        try:
            client_sock, address = self.s.accept()
            response, leftover = ntwrk.receive(client_sock)
            if response.getFlag():
                message = Message.from_yaml(response.getData())
                request = message.get_body()
                try:
                    if hasattr(self, request['action']) and message.get_header("node_id") != self.node_id:
                        kwargs = copy.deepcopy(request)
                        if request['action'] == 'greetings':
                            kwargs['__remote_ip__'] = client_sock.getpeername()
                        del kwargs['action']
                        result = getattr(self, request['action'])(**kwargs)
                    else:
                        result = 'Received action is not valid'
                except:
                    result = 'Something went wrong while evaluating.\n'
                    tools.log(sys.exc_info())
                response = Message(headers={'ack': message.get_header('id'),
                                            'node_id': self.node_id},
                                   body=result)
                ntwrk.send(response, client_sock)
                client_sock.close()
        except:
            pass

    @sync
    def greetings(self, node_id, port, __remote_ip__):
        """
        Called when a peer starts communicating with us.
        If it is a new node, we should add it to our peer list.

        :param node_id:
        :param port:
        :param __remote_ip__:
        :return:
        """
        from halocoin.account import AccountService
        peer = copy.deepcopy(AccountService.default_peer)
        peer['node_id'] = node_id
        peer['ip'] = __remote_ip__[0]
        peer['port'] = port
        self.account.add_peer(peer)
        return True

    @sync
    def receive_peer(self, peer):
        self.account.add_peer(peer)

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
        return self.account.get_peers()

    @sync
    def txs(self):
        return self.blockchain.tx_pool()

    @sync
    def push_tx(self, tx):
        self.blockchain.tx_queue.put(tx)
        return 'success'

    @sync
    def push_block(self, blocks):
        self.blockchain.blocks_queue.put(blocks)
        return 'success'

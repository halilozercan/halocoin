import copy
import socket
import sys
import uuid

from halocoin import ntwrk, custom
from halocoin import tools
from halocoin.db_client import ClientDB
from halocoin.ntwrk import Message
from halocoin.service import Service


class PeerListenService(Service):
    actions = ['greetings', 'receive_peer', 'block_count', 'range_request', 'peers', 'txs', 'push_tx', 'push_block']

    def __init__(self, engine):
        Service.__init__(self, 'peer_receive')
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.clientdb = None
        self.node_id = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.clientdb = self.engine.clientdb

        if not self.db.exists('node_id'):
            self.db.put('node_id', str(uuid.uuid4()))

        self.node_id = self.db.get('node_id')

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.settimeout(2)
            self.s.bind((self.engine.config['peers']['host'], self.engine.config['peers']['port']))
            self.s.listen(10)
            print("Started Peer Listen on {}:{}".format(self.engine.config['peers']['host'],
                                                        self.engine.config['peers']['port']))
            return True
        except Exception as e:
            tools.log("Could not start Peer Receive socket!")
            tools.log(e)
            sys.stderr.write(str(e)+'\n')
            return False

    def on_close(self):
        try:
            self.s.close()
        except:
            pass
        Service.on_close(self)

    def loop(self):
        try:
            client_sock, address = self.s.accept()
            response, leftover = ntwrk.receive(client_sock)
            if not response.getFlag():
                return
            message = Message.from_str(response.getData())
            request = message.get_body()

            try:
                if request['action'] not in PeerListenService.actions \
                        or request['version'] != custom.version \
                        or message.get_header("node_id") == self.node_id:
                    result = 'Received action is not valid'
                elif request['action'] == 'greetings':
                    result = self.greetings(request['node_id'],
                                            request['port'],
                                            request['length'],
                                            request['diffLength'],
                                            client_sock.getpeername())
                elif request['action'] == 'push_block':
                    result = self.push_block(request['blocks'],
                                             message.get_header("node_id"))
                elif request['action'] == 'receive_peer':
                    result = self.receive_peer(request['peer'])
                elif request['action'] == 'block_count':
                    result = self.block_count()
                elif request['action'] == 'range_request':
                    result = self.range_request(request['range'])
                elif request['action'] == 'peers':
                    result = self.peers()
                elif request['action'] == 'txs':
                    result = self.txs()
                elif request['action'] == 'push_tx':
                    result = self.push_tx(request['tx'])
                elif request['action'] == 'push_block':
                    result = self.push_block(request['blocks'], message.get_header('node_id'))
                else:
                    result = "Unknown action"
            except Exception as e:
                result = 'Something went wrong while evaluating.\n' + str(e)
                tools.log(sys.exc_info())
            response = Message(headers={'ack': message.get_header('id'),
                                        'node_id': self.node_id},
                               body=result)
            ntwrk.send(response, client_sock)
            client_sock.close()
        except Exception as e:
            import time
            time.sleep(0.1)

    def greetings(self, node_id, port, length, diffLength, __remote_ip__):
        """
        Called when a peer starts communicating with us.
        'Greetings' type peer addition.

        :param node_id: Node id of remote host
        :param port: At which port they are listening to peers.
        :param __remote_ip__: IP address of remote as seen from this network.
        :return: Our own greetings message
        """
        peer = copy.deepcopy(ClientDB.default_peer)
        peer.update(
            node_id=node_id,
            ip=__remote_ip__[0],
            port=port,
            length=length,
            diffLength=diffLength,
            rank=0.75
        )
        if length > self.clientdb.get('known_length'):
            self.clientdb.put('known_length', length)
        self.clientdb.add_peer(peer, 'greetings')
        return {
            'node_id': self.node_id,
            'port': self.engine.config['peers']['port'],
            'length': self.db.get('length'),
            'diffLength': self.db.get('diffLength')
        }

    def receive_peer(self, peer):
        """
        'Friend of mine' type peer addition.
        :param peer: a peer dict, sent by another peer we are communicating with.
        :return: None
        """
        peer.update(rank=1)  # We do not care about earlier rank.
        self.clientdb.add_peer(peer, 'friend_of_mine')

    def block_count(self):
        length = self.db.get('length')
        d = '0'
        if length >= 0:
            d = self.db.get('diffLength')
        return {'length': length, 'diffLength': d}

    def range_request(self, range):
        out = []
        counter = 0
        while range[0] + counter <= range[1]:
            block = self.blockchain.get_block(range[0] + counter)
            if block and 'length' in block:
                out.append(block)
            counter += 1
        return out

    def peers(self):
        return self.clientdb.get_peers()

    def txs(self):
        return self.blockchain.tx_pool()

    def push_tx(self, tx):
        self.blockchain.tx_queue.put(tx)
        return 'success'

    def push_block(self, blocks, node_id):
        self.blockchain.blocks_queue.put((blocks, node_id))
        return 'success'

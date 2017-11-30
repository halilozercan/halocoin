import socket
import time
import uuid
from threading import Thread

from halocoin import blockchain
from halocoin import ntwrk
from halocoin import tools
from halocoin.ntwrk import command
from halocoin.service import Service, threaded, sync


class PeerCheckService(Service):
    def __init__(self, engine, trackers):
        # This logic might change. Here we add new peers while initializing the service
        Service.__init__(self, 'peers_check')
        self.engine = engine
        self.trackers = trackers
        self.db = None
        self.blockchain = None
        self.account = None
        self.node_id = "Anon"
        self.old_peers = []
        self.last_tracker_connection = 0

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account

        if not self.db.exists('node_id'):
            self.db.put('node_id', str(uuid.uuid4()))

        self.node_id = self.db.get('node_id')
        return True

    @threaded
    def listen(self):
        if self.should_check_trackers():
            self.check_trackers()

        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        peers = self.account.get_peers()
        if len(peers) > 0:
            i = tools.exponential_random(1.0 / 2) % len(peers)
            peer = peers[i]
            t1 = time.time()
            r = self.peer_check(peer)
            t2 = time.time()

            peer['rank'] *= 0.8
            if r == 0:
                peer['rank'] += 0.2 * (t2 - t1)
            else:
                peer['rank'] += 0.2 * 30

            self.account.update_peer(peer)

    def should_check_trackers(self):
        return time.time() - self.last_tracker_connection > 5

    def check_trackers(self):
        try:
            for tracker in self.trackers:
                sa = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sa.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sa.connect((tracker['ip'], tracker['port']))
                sa.settimeout(10)
                priv_addr = sa.getsockname()

                priv_info = {
                    "ip": priv_addr[0],
                    "port": priv_addr[1],
                    "node_id": self.node_id
                }
                pub_info = command(('', ''), priv_info, self.node_id, sock=sa)
                clients = command(('', ''), {"ip": pub_info["ip"], "port": pub_info["port"], "node_id": self.node_id},
                                  self.node_id, sock=sa)
                for node_id in clients.keys():
                    clients[node_id]['node_id'] = node_id
                    self.account.add_peer(clients[node_id])
                self.db.put('priv_info', priv_info)
                sa.close()
            self.last_tracker_connection = time.time()
        except Exception as e:
            pass

    def peer_check(self, peer):
        priv_info = self.db.get('priv_info')
        threads = {
            '0_accept': Thread(target=self.accept, args=(priv_info['port'],)),
            '1_accept': Thread(target=self.accept, args=(peer['pub_port'],)),
            '2_connect': Thread(target=self.connect,
                                args=((priv_info['ip'], priv_info['port']), (peer['pub_ip'], peer['pub_port']),)),
            '3_connect': Thread(target=self.connect,
                                args=((priv_info['ip'], priv_info['port']), (peer['priv_ip'], peer['priv_port']),)),
        }
        for name in sorted(threads.keys()):
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

        return

        peer_ip_port = (peer['ip'], peer['port'])

        block_count = ntwrk.command(peer_ip_port, {'action': 'block_count'}, self.node_id)

        if not isinstance(block_count, dict):
            return
        if 'error' in block_count.keys():
            return

        peer['diffLength'] = block_count['diffLength']
        peer['length'] = block_count['length']
        self.account.update_peer(peer)

        known_length = self.db.get('known_length')
        if block_count['length'] > known_length:
            self.db.put('known_length', block_count['length'])

        length = self.db.get('length')
        diff_length = self.db.get('diffLength')
        size = max(len(diff_length), len(block_count['diffLength']))
        us = tools.buffer_(diff_length, size)
        them = tools.buffer_(block_count['diffLength'], size)
        # This is the most important peer operation part
        # We are deciding what to do with this peer. We can either
        # send them blocks, share txs or download blocks.
        if them < us:
            self.give_block(peer_ip_port, block_count['length'])
        elif us == them:
            self.ask_for_txs(peer_ip_port)
        else:
            self.download_blocks(peer_ip_port, block_count, length)

        my_peers = self.account.get_peers()
        their_peers = ntwrk.command(peer_ip_port, {'action': 'peers'}, self.node_id)
        if type(their_peers) == list:
            for p in their_peers:
                self.account.add_peer(p)
            for p in my_peers:
                ntwrk.command(peer_ip_port, {'action': 'receive_peer', 'peer': p}, self.node_id)

        return 0

    def download_blocks(self, peer_ip_port, peers_block_count, length):
        b = [max(0, length - 10), min(peers_block_count['length'] + 1,
                                      length + self.engine.config['download_limit'])]
        blocks = ntwrk.command(peer_ip_port, {'action': 'range_request', 'range': b}, self.node_id)
        if not isinstance(blocks, list):
            return []
        self.blockchain.blocks_queue.put(blocks)
        return 0

    def ask_for_txs(self, peer_ip_port):
        T = self.blockchain.tx_pool()
        pushers = filter(lambda t: t not in txs, T)
        for push in pushers:
            ntwrk.command(peer_ip_port, {'action': 'push_tx', 'tx': push}, self.node_id)

        txs = ntwrk.command(peer_ip_port, {'action': 'txs'}, self.node_id)
        if not isinstance(txs, list):
            return -1
        for tx in txs:
            self.blockchain.tx_queue.put(tx)
        return 0

    def give_block(self, peer_ip_port, block_count_peer):
        blocks = []
        b = [max(block_count_peer - 5, 0), min(self.db.get('length'),
                                               block_count_peer + self.engine.config['download_limit'])]
        for i in range(b[0], b[1] + 1):
            blocks.append(self.db.get(i))
        ntwrk.command(peer_ip_port, {'action': 'push_block', 'blocks': blocks}, self.node_id)
        return 0

    def accept(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(('', port))
        s.listen(1)
        s.settimeout(5)
        while True:
            try:
                conn, addr = s.accept()
            except Exception as e:
                s.close()
                break

    def connect(self, local_addr, addr):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(local_addr)
        while True:
            try:
                s.connect(addr)
            except Exception as e:
                s.close()
                break
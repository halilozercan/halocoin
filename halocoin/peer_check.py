import time

from halocoin import blockchain
from halocoin import ntwrk
from halocoin import tools
from halocoin.service import Service, threaded, sync


class PeerCheckService(Service):
    def __init__(self, engine, new_peers):
        # This logic might change. Here we add new peers while initializing the service
        Service.__init__(self, 'peers_check')
        self.engine = engine
        self.new_peers = []
        self.new_peers = new_peers
        self.db = None
        self.blockchain = None
        self.account = None
        self.node_id = "Anon"
        self.old_peers = []

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account
        for peer in self.new_peers:
            self.account.add_peer(peer, 'friend_of_mine')
        self.node_id = self.db.get('node_id')
        print("Started Peers Check")
        return True

    @threaded
    def listen(self):
        """
        Pseudorandomly select a peer to check.
        If blockchain is synchronizing, don't check anyone.
        :return:
        """
        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        peers = self.account.get_peers()
        if len(peers) > 0:
            i = tools.exponential_random(1.0 / 2.5) % len(peers)
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

    @sync
    def peer_check(self, peer):
        peer_ip_port = (peer['ip'], peer['port'])
        greeted = ntwrk.command(peer_ip_port,
                                {
                                    'action': 'greetings',
                                    'node_id': self.node_id,
                                    'port': self.engine.config['port']['peers'],
                                    'length': self.db.get('length'),
                                    'diffLength': self.db.get('diffLength')
                                },
                                self.node_id)

        if not isinstance(greeted, dict):
            return
        if 'error' in greeted.keys():
            return

        peer['diffLength'] = greeted['diffLength']
        peer['length'] = greeted['length']
        self.account.update_peer(peer)

        known_length = self.db.get('known_length')
        if greeted['length'] > known_length:
            self.db.put('known_length', greeted['length'])

        length = self.db.get('length')
        diff_length = self.db.get('diffLength')
        size = max(len(diff_length), len(greeted['diffLength']))
        us = tools.buffer_(diff_length, size)
        them = tools.buffer_(greeted['diffLength'], size)
        # This is the most important peer operation part
        # We are deciding what to do with this peer. We can either
        # send them blocks, share txs or download blocks.
        if them < us:
            self.give_block(peer_ip_port, greeted['length'])
        elif us == them:
            self.ask_for_txs(peer_ip_port)
        else:
            self.download_blocks(peer_ip_port, greeted['length'], length)

        my_peers = self.account.get_peers()
        their_peers = ntwrk.command(peer_ip_port, {'action': 'peers'}, self.node_id)
        if type(their_peers) == list:
            for p in their_peers:
                self.account.add_peer(p, 'friend_of_mine')
            for p in my_peers:
                ntwrk.command(peer_ip_port, {'action': 'receive_peer', 'peer': p}, self.node_id)

        return 0

    def download_blocks(self, peer_ip_port, block_count_peer, length):
        b = [max(0, length - 10), min(block_count_peer + 1,
                                      length + self.engine.config['peers']['download_limit'])]
        blocks = ntwrk.command(peer_ip_port, {'action': 'range_request', 'range': b}, self.node_id)
        if not isinstance(blocks, list):
            return []
        self.blockchain.blocks_queue.put(blocks)
        return 0

    def ask_for_txs(self, peer_ip_port):
        T = self.blockchain.tx_pool()
        pushers = list(filter(lambda t: t not in txs, T))
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
                                               block_count_peer + self.engine.config['peers']['download_limit'])]
        for i in range(b[0], b[1] + 1):
            blocks.append(self.db.get(i))
        ntwrk.command(peer_ip_port, {'action': 'push_block', 'blocks': blocks}, self.node_id)
        return 0

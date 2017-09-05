import time

import blockchain
import ntwrk
import tools
from service import Service, threaded, sync


class PeerCheckService(Service):
    def __init__(self, engine, new_peers):
        # This logic might change. Here we add new peers while initializing the service
        Service.__init__(self, 'peers_check')
        self.engine = engine
        self.new_peers = []
        for new_peer in new_peers:
            self.new_peers.append([new_peer, 5, '0', 0])
        self.db = None
        self.blockchain = None
        self.account = None
        self.old_peers = []

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account
        for peer in self.new_peers:
            self.account.add_peer(peer)
        return True

    @threaded
    def listen(self):
        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        peers = self.account.get_peers()
        if len(peers) > 0:
            pr = sorted(peers, key=lambda x: x[1], reverse=True)

            i = tools.exponential_random(3.0 / 4) % len(pr)
            peer = pr[i]
            t1 = time.time()
            r = self.peer_check(peer)
            t2 = time.time()

            peer[1] *= 0.8
            if r == 0:
                peer[1] += 0.2 * (t2 - t1)
            else:
                peer[1] += 0.2 * 30
            self.account.update_peer(peer)

    @sync
    def peer_check(self, peer):
        block_count = ntwrk.command(peer[0], {'action': 'block_count'})

        if not isinstance(block_count, dict):
            return
        if 'error' in block_count.keys():
            return

        peer[2] = block_count['diffLength']
        peer[3] = block_count['length']
        self.account.update_peer(peer)

        length = self.db.get('length')
        diff_length = self.db.get('diffLength')
        size = max(len(diff_length), len(block_count['diffLength']))
        us = tools.buffer_(diff_length, size)
        them = tools.buffer_(block_count['diffLength'], size)
        # This is the most important peer operation part
        # We are deciding what to do with this peer. We can either
        # send them blocks, share txs or download blocks.
        if them < us:
            self.give_block(peer[0], block_count['length'])
        elif us == them:
            self.ask_for_txs(peer[0])
        else:
            self.download_blocks(peer[0], block_count, length)

        my_peers = self.account.get_peers()
        their_peers = ntwrk.command(peer[0], {'action': 'peers'})
        if type(their_peers) == list:
            for p in their_peers:
                self.account.add_peer(p)
            for p in my_peers:
                ntwrk.command(peer[0], {'action': 'receive_peer', 'peer': p})

    def download_blocks(self, peer, peers_block_count, length):
        known_length = self.db.get('known_length')
        if peers_block_count['length'] > known_length:
            self.db.put('known_length', peers_block_count['length'])
        b = [max(0, length - 10), min(peers_block_count['length'] + 1,
                                      length + self.engine.config['peer.block_request_limit'])]
        blocks = ntwrk.command(peer, {'action': 'range_request', 'range': b})
        if not isinstance(blocks, list):
            return []
        self.blockchain.blocks_queue.put(blocks)
        return 0

    def ask_for_txs(self, peer):
        txs = ntwrk.command(peer, {'action': 'txs'})
        if not isinstance(txs, list):
            return -1
        for tx in txs:
            self.blockchain.tx_queue.put(tx)
        T = self.blockchain.tx_pool()
        pushers = filter(lambda t: t not in txs, T)
        for push in pushers:
            ntwrk.command(peer, {'action': 'pushtx', 'tx': push})
        return 0

    def give_block(self, peer, block_count_peer):
        blocks = []
        b = [max(block_count_peer - 5, 0), min(self.db.get('length'),
                                               block_count_peer + self.engine.config['peer.block_request_limit'])]
        for i in range(b[0], b[1] + 1):
            blocks.append(self.db.get(i))
        ntwrk.command(peer, {'action': 'pushblock',
                             'blocks': blocks})
        return 0

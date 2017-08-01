"""We regularly check on peers to see if they have mined new blocks.
This file explains how we initiate interactions with our peers.
"""
import time

import ntwrk
import tools
from blockchain import BlockchainService
from service import Service, threaded, sync


class PeerCheckService(Service):
    def __init__(self, engine, new_peers):
        # This logic might change. Here we add new peers while initializing the service
        Service.__init__(self, 'peers_check')
        self.engine = engine
        self.new_peers = new_peers
        self.db = None
        self.blockchain = None
        self.old_peers = []

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.old_peers = self.db.get('peers_ranked')
        for peer in self.new_peers:
            self.old_peers = tools.add_peer_ranked(peer, self.old_peers)
        self.db.put('peers_ranked', self.old_peers)
        return True

    @threaded
    def listen(self):
        if len(self.old_peers) > 0:
            # Sort old peers by their rank. r[2] contains rank number.
            pr = sorted(self.old_peers, key=lambda r: r[2])
            # Reverse because high rank number means lower quality
            pr.reverse()

            i = tools.exponential_random(3.0 / 4) % len(pr)
            t1 = time.time()
            r = self.peer_check(i, pr)
            t2 = time.time()
            p = pr[i][0]
            pr = self.db.get('peers_ranked')
            for peer in pr:
                if peer[0] == p:
                    pr[i][1] *= 0.8
                    if r == 0:
                        pr[i][1] += 0.2 * (t2 - t1)
                    else:
                        pr[i][1] += 0.2 * 30
            self.db.put('peers_ranked', pr)

    @sync
    def peer_check(self, i, peers):
        peer = peers[i][0]
        block_count = ntwrk.command(peer, {'action': 'block_count'})

        if not isinstance(block_count, dict):
            return
        if 'error' in block_count.keys():
            return

        peers[i][2] = block_count['diffLength']
        peers[i][3] = block_count['length']
        self.db.put('peers_ranked', peers)
        length = self.db.get('length')
        diff_length = self.db.get('diffLength')
        size = max(len(diff_length), len(block_count['diffLength']))
        us = tools.buffer_(diff_length, size)
        them = tools.buffer_(block_count['diffLength'], size)
        # This is the most important peer operation part
        # We are deciding what to do with this peer. We can either
        # send them blocks, share txs or download blocks.
        if them < us:
            self.give_block(peer, block_count['length'])
        elif us == them:
            self.ask_for_txs(peer)
        else:
            self.download_blocks(peer, block_count, length)
        flag = False
        my_peers = self.db.get('peers_ranked')
        their_peers = ntwrk.command(peer, {'action': 'peers'})
        if type(their_peers) == list:
            for p in their_peers:
                if p not in my_peers:
                    flag = True
                    my_peers.append(p)
            for p in my_peers:
                if p not in their_peers:
                    ntwrk.command(peer, {'action': 'receive_peer', 'peer': p})
        if flag:
            self.db.put('peers_ranked', my_peers)

    def download_blocks(self, peer, peers_block_count, length):
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
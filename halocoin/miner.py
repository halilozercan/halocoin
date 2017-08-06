""" This file mines blocks and talks to peers. It maintains consensus of the
    blockchain.
"""
import json
import random
import subprocess
import tempfile
import time

import blockchain
import custom
import tools
from ntwrk import Response
from service import Service, threaded


class MinerService(Service):
    def __init__(self, engine):
        Service.__init__(self, "miner")
        self.engine = engine
        self.db = None
        self.blockchain = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        return True

    @threaded
    def worker(self):
        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        candidate_block = self.get_candidate_block()
        f = tempfile.NamedTemporaryFile()
        f.write(json.dumps(candidate_block))
        f.flush()
        p = subprocess.Popen([custom.miner, f.name], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        possible_block = None
        tx_pool = self.blockchain.tx_pool()
        while self.threaded_running():
            if p.poll() is not None:
                possible_block = json.load(open(f.name + '_mined', 'r'))
                break
            else:
                time.sleep(1)

            if self.blockchain.tx_pool() != tx_pool:
                f.seek(0)
                candidate_block = self.get_candidate_block()
                json.dump(candidate_block, f)
                p.kill()
                p = subprocess.Popen([custom.miner, f.name], shell=True, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if p.poll() is None:
            p.kill()

        if possible_block is not None:
            tools.log('Mined block')
            tools.log(possible_block)
            self.blockchain.blocks_queue.put(possible_block)

    def make_block(self, prev_block, txs, pubkey):
        leng = int(prev_block['length']) + 1
        target_ = self.blockchain.target(leng)
        print 'target', target_
        diffLength = blockchain.hex_sum(prev_block['diffLength'],
                                        blockchain.hex_invert(target_))
        out = {'version': custom.version,
               'txs': txs + [self.make_mint(pubkey)],
               'length': leng,
               'time': time.time(),
               'diffLength': diffLength,
               'target': target_,
               'prevHash': tools.det_hash(prev_block)}
        return out

    def make_mint(self, pubkey):
        return {'type': 'mint',
                'pubkeys': [pubkey],
                'signatures': ['first_sig'],
                'count': 0}

    def genesis(self, pubkey):
        target_ = self.blockchain.target(0)
        out = {'version': custom.version,
               'length': 0,
               'time': time.time(),
               'target': target_,
               'diffLength': blockchain.hex_invert(target_),
               'txs': [self.make_mint(pubkey)]}
        return out

    def proof_of_work(self, block):
        if 'nonce' in block:
            block.pop('nonce')
        halfHash = tools.det_hash(block)
        block['nonce'] = random.randint(0, 10000000000000000000000000000000000000000)
        count = 0
        current_hash = tools.det_hash({'nonce': block['nonce'], 'halfHash': halfHash})
        while current_hash > block['target'] and self.threaded_running() and count < 100000:
            count += 1
            block['nonce'] += 1
            current_hash = tools.det_hash({'nonce': block['nonce'], 'halfHash': halfHash})

        if current_hash <= block['target']:
            return Response(True, block)
        else:
            return Response(False, None)

    def get_candidate_block(self):
        length = self.db.get('length')
        print 'Miner working for block', (length + 1)
        if length == -1:
            candidate_block = self.genesis(self.db.get('pubkey'))
        else:
            prev_block = self.db.get(length)
            candidate_block = self.make_block(prev_block, self.blockchain.tx_pool(), self.db.get('pubkey'))
        return candidate_block

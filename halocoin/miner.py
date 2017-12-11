import multiprocessing
import queue
import random
import time
from multiprocessing import Process

from halocoin import blockchain
from halocoin import custom
from halocoin import tools
from halocoin.service import Service, threaded


class MinerService(Service):
    """
    Simple miner service. Starts running when miner is turned on.
    Executes number of workers as specified in config.
    Workers are run as different processes. Supports multicore mining.
    """
    def __init__(self, engine):
        Service.__init__(self, "miner")
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.wallet = None
        config_cores = self.engine.config['miner']['cores']
        self.core_count = multiprocessing.cpu_count() if config_cores == -1 else config_cores
        self.pool = []
        self.queue = multiprocessing.Queue()

    def set_wallet(self, wallet):
        self.wallet = wallet

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

        if self.wallet is not None and hasattr(self.wallet, 'privkey'):
            return True
        else:
            return False

    def on_close(self):
        self.wallet = None
        self.close_workers()
        print('Miner is turned off')

    @threaded
    def worker(self):
        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        candidate_block = self.get_candidate_block()
        tx_pool = self.blockchain.tx_pool()
        self.start_workers(candidate_block)

        possible_blocks = []
        while not MinerService.is_everyone_dead(self.pool) and self.threaded_running():
            if self.db.get('length')+1 != candidate_block['length'] or self.blockchain.tx_pool() != tx_pool:
                candidate_block = self.get_candidate_block()
                tx_pool = self.blockchain.tx_pool()
                self.start_workers(candidate_block)
            try:
                while not self.queue.empty():
                    possible_blocks.append(self.queue.get(timeout=0.01))
            except queue.Empty:
                pass
            if len(possible_blocks) > 0:
                break

        # This may seem weird. It is needed when workers finish so fast, while loop ends prematurely.
        try:
            while not self.queue.empty():
                possible_blocks.append(self.queue.get(timeout=0.01))
        except queue.Empty:
            pass

        if len(possible_blocks) > 0:
            tools.log('Mined block')
            tools.log(possible_blocks)
            self.blockchain.blocks_queue.put(possible_blocks)

    def start_workers(self, candidate_block):
        self.close_workers()
        for i in range(self.core_count):
            p = Process(target=MinerService.target, args=[candidate_block, self.queue])
            p.start()
            self.pool.append(p)

    def close_workers(self):
        for p in self.pool:
            p.terminate()
            p.join()
        self.pool = []

    def make_block(self, prev_block, txs, pubkey):
        leng = int(prev_block['length']) + 1
        target_ = self.blockchain.target(leng)
        diffLength = tools.hex_sum(prev_block['diffLength'], tools.hex_invert(target_))
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
               'diffLength': tools.hex_invert(target_),
               'txs': [self.make_mint(pubkey)]}
        return out

    def get_candidate_block(self):
        length = self.db.get('length')
        print('Miner working for block', (length + 1))
        if length == -1:
            candidate_block = self.genesis(self.wallet.get_pubkey_str())
        else:
            prev_block = self.db.get(length)
            candidate_block = self.make_block(prev_block, self.blockchain.tx_pool(), self.wallet.get_pubkey_str())
        return candidate_block

    @staticmethod
    def target(candidate_block, queue):
        # Miner registered but no work is sent yet.
        try:
            if candidate_block is None:
                return
            if 'nonce' in candidate_block:
                candidate_block.pop('nonce')
            halfHash = tools.det_hash(candidate_block)
            candidate_block['nonce'] = random.randint(0, 10000000000000000000000000000000000000000)
            current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
            while current_hash > candidate_block['target']:
                candidate_block['nonce'] += 1
                current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
            if current_hash <= candidate_block['target']:
                queue.put(candidate_block)
        except Exception as e:
            pass

    @staticmethod
    def is_everyone_dead(processes):
        for p in processes:
            if p.is_alive():
                return False
        return True

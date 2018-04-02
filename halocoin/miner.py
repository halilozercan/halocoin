import multiprocessing
import random
import signal
import time
from multiprocessing import Process

from halocoin import custom, api
from halocoin import tools
from halocoin.service import Service, lockit


def preexec_function():
    # Ignore the SIGINT signal by setting the handler to the standard
    # signal handler SIG_IGN.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


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
        self.statedb = None
        self.wallet = None
        config_cores = self.engine.config['miner']['cores']
        self.core_count = multiprocessing.cpu_count() if config_cores == -1 else config_cores
        self.pool = []
        self.queue = multiprocessing.Queue()
        self.status_description = "Initialized"

    def set_wallet(self, wallet):
        self.wallet = wallet

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.statedb = self.engine.statedb

        if self.wallet is not None and hasattr(self.wallet, 'privkey'):
            self.status_description = "Registered"
            return True
        else:
            return False

    def on_close(self):
        self.status_description = "Closed"
        self.wallet = None
        self.close_workers()
        Service.on_close(self)
        print('Miner is turned off')

    def get_status(self):
        status = Service.get_status(self)
        status['description'] = self.status_description
        return status

    def loop(self):
        self.status_description = 'Miner preparing block %d' % (self.db.get('length') + 1)
        print(self.status_description)

        candidate_block = self.get_candidate_block()

        self.status_description = 'Miner starting to work for block %d' % (candidate_block['length'])
        print(self.status_description)

        self.start_workers(candidate_block)

        possible_blocks = []
        while self.get_state() == Service.RUNNING and (self.db.get('length')+1) == candidate_block['length']:
            api.miner_status()
            while not self.queue.empty():
                possible_blocks.append(self.queue.get(timeout=0.01))
            time.sleep(0.1)
            if len(possible_blocks) > 0:
                tools.log('Mined block')
                tools.log(possible_blocks[:1])
                self.blockchain.blocks_queue.put((possible_blocks[:1], 'miner'))
                break

    def start_workers(self, candidate_block):
        self.close_workers()
        for i in range(self.core_count):
            p = Process(target=MinerService.target, args=[candidate_block, self.queue])
            p.start()
            self.pool.append(p)

    def close_workers(self):
        for p in self.pool:
            p.terminate()
        self.pool = []

    def make_block(self, prev_block, txs, pubkey):
        """
        After mempool changes at 0.011c version, make block must select valid transactions.
        Mempool is mixed and not all transactions may be valid at the same time.
        Miner creates a block by adding transactions that are valid together.
        :param prev_block:
        :param txs:
        :param pubkey:
        :return:
        """
        leng = int(prev_block['length']) + 1
        target_ = self.blockchain.target(leng)
        diffLength = tools.hex_sum(prev_block['diffLength'], tools.hex_invert(target_))
        txs = self.statedb.get_valid_txs_for_next_block(txs, leng)
        txs = [self.make_mint(pubkey)] + txs
        out = {'version': custom.version,
               'txs': txs,
               'length': leng,
               'time': time.time(),
               'diffLength': diffLength,
               'target': target_,
               'prevHash': tools.det_hash(prev_block)}
        return out

    def make_mint(self, pubkey):
        return {'type': 'mint',
                'version': custom.version,
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

    @lockit('write_kvstore')
    def get_candidate_block(self):
        length = self.db.get('length')
        if length == -1:
            candidate_block = self.genesis(self.wallet.get_pubkey_str())
        else:
            prev_block = self.blockchain.get_block(length)
            candidate_block = self.make_block(prev_block, self.blockchain.tx_pool(), self.wallet.get_pubkey_str())
        return candidate_block

    @staticmethod
    def target(_candidate_block, queue):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # Miner registered but no work is sent yet.
        import copy
        candidate_block = copy.deepcopy(_candidate_block)
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
            tools.log('Miner ran into a problem ' + str(e))
            pass

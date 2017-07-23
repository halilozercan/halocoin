""" This file explains explains the rules for adding and removing blocks from the local chain.
"""
import Queue
import copy
import time
import custom
import database
import services
import target
import tools
import transactions
import network

from service import Service, threaded, sync


def add_tx(tx, DB=None):
    def verify_count(tx):
        return tx['count'] != tools.count(address, DB)

    def type_check(tx):
        if not tools.E_check(tx, 'type', [str, unicode]):
            out[0] += 'blockchain type'
            return False
        if tx['type'] == 'mint':
            return False
        if tx['type'] not in transactions.tx_check:
            out[0] += 'bad type'
            return False
        return True

    def too_big_block(tx, txs):
        return len(tools.package(txs + [tx])) > network.MAX_MESSAGE_SIZE - 5000

    def verify_tx(tx, txs, out):
        if not type_check(tx):
            out[0] += 'type error'
            return False
        if tx in txs:
            out[0] += 'no duplicates'
            return False
        if verify_count(tx):
            out[0] += 'count error'
            return False
        if too_big_block(tx, txs):
            out[0] += 'too many txs'
            return False
        if not transactions.tx_check[tx['type']](tx, txs, out, DB):
            out[0] += 'tx: ' + str(tx)
            return False
        return True

    if DB is None:
        DB = {}

    # Attempt to add a new transaction into the pool.
    # print('top of add_tx')
    out = ['']
    if not isinstance(tx, dict):
        return False
    address = tools.make_address(tx['pubkeys'], len(tx['signatures']))

    # tools.log('attempt to add tx: ' +str(tx))
    T = tools.db_get('txs')
    if verify_tx(tx, T, out):
        T.append(tx)
        tools.db_put('txs', T)
        return 'added tx: ' + str(tx)
    else:
        return 'failed to add tx because: ' + out[0]


def recent_blockthings(storage, size, length):
    def get_val(length):
        leng = str(length)
        if not leng in storage:
            block = tools.db_get(leng)
            if block == database.default_entry():
                if leng == tools.db_get('length'):
                    tools.db_put('length', int(leng) - 1)
                    block = tools.db_get(leng)
                else:
                    error()
            # try:
            storage[leng] = tools.db_get(leng)[key[:-1]]
            tools.db_put(key, storage)
        return storage[leng]

    def clean_up(storage, end):
        if end < 0: return
        if not str(end) in storage:
            return
        else:
            storage.pop(str(end))
            return clean_up(storage, end - 1)

    start = max((length - size), 0)
    clean_up(storage, length - max(custom.mmm, custom.history_length) - 100)
    return map(get_val, range(start, length))


def hex_sum(a, b):
    # Sum of numbers expressed as hexidecimal strings
    return tools.buffer_(str(hex(int(a, 16) + int(b, 16)))[2: -1], 64)


def hex_invert(n):
    # Use double-size for division, to reduce information leakage.
    return tools.buffer_(str(hex(int('f' * 128, 16) / int(n, 16)))[2: -1], 64)


def delete_block(DB):
    """ Removes the most recent block from the blockchain. """
    length = tools.db_get('length')
    if length < 0:
        return
    try:
        ts = tools.db_get('targets')
        ts.pop(str(length))
        tools.db_put('targets', ts)
    except:
        pass
    try:
        ts = tools.db_get('times')
        ts.pop(str(length))
        tools.db_put('times', ts)
    except:
        pass
    block = tools.db_get(length)
    orphans = tools.db_get('txs')
    tools.db_put('txs', [])
    for tx in block['txs']:
        orphans.append(tx)
        tools.db_put('add_block', False)
        transactions.update[tx['type']](tx, DB, False)
    tools.db_delete(length)
    length -= 1
    tools.db_put('length', length)
    if length == -1:
        tools.db_put('diffLength', '0')
    else:
        block = tools.db_get(length)
        tools.db_put('diffLength', block['diffLength'])
    for orphan in sorted(orphans, key=lambda x: x['count']):
        add_tx(orphan, DB)
        # while tools.db_get('length')!=length:
        #    time.sleep(0.0001)


def profile(DB):
    import cProfile
    import pprint
    p = cProfile.Profile()
    p.run('blockchain.main(custom.DB)')
    g = p.getstats()
    # g=g.sorted(lambda x: x.inlinetime)
    g = sorted(g, key=lambda x: x.totaltime)
    g.reverse()
    pprint.pprint(g)
    # return f(DB['suggested_blocks'], DB['suggested_txs'])


class BlockchainService(Service):
    def __init__(self, config):
        Service.__init__(self, name='blockchain')
        self.config = config
        self.blocks_queue = Queue.Queue()
        self.tx_queue = Queue.Queue()
        self.db = services.get('database')

    @threaded
    def process(self):
        if self.db.get('stop'):
            self.close_threaded()
        if not self.blocks_queue.empty():
            candidate_block = self.blocks_queue.get()
            self.add_block(candidate_block)
        elif not self.tx_queue.empty():
            candidate_tx = self.tx_queue.get()
            self.add_tx(candidate_tx)

    @sync
    def add_block(self, block):
        """Attempts adding a new block to the blockchain.
         Median is good for weeding out liars, so long as the liars don't have 51%
         hashpower. """

        def block_check(block):
            def log_(txt):
                pass  # return tools.log(txt)

            def tx_check(txs):
                start = copy.deepcopy(txs)
                out = []
                start_copy = []
                while start != start_copy:
                    if start == []:
                        return False  # Block passes this test
                    start_copy = copy.deepcopy(start)
                    if transactions.tx_check[start[-1]['type']](start[-1], out, [''], DB):
                        out.append(start.pop())
                    else:
                        return True  # Block is invalid
                return True  # Block is invalid

            if not isinstance(block, dict):
                return False

            if 'error' in block:
                return False

            if not ('length' in block and isinstance(block['length'], int)):
                return False

            length = self.db.get('length')

            if int(block['length']) != int(length) + 1:
                return False

            # TODO: understand what is going on here
            if block['diffLength'] != hex_sum(self.db.get('diffLength'),
                                              hex_invert(block['target'])):
                return False

            if length >= 0:
                if tools.det_hash(self.db.get(length)) != block['prevHash']:
                    return False

            if 'target' not in block.keys():
                return False

            nonce_and_hash = tools.hash_without_nonce(block)
            if tools.det_hash(nonce_and_hash) > block['target']:
                return False

            if block['target'] != target.target(block['length']):
                log_('block: ' + str(block))
                log_('target: ' + str(target.target(block['length'])))
                log_('wrong target')
                return False

            earliest = tools.median(recent_blockthings(self.db.get('times'), custom.mmm, self.db.get('length')))
            if 'time' not in block:
                log_('no time')
                return False
            if block['time'] > time.time() + 60 * 6:
                log_('too late')
                return False
            if block['time'] < earliest:
                log_('too early')
                return False
            if tx_check(block['txs']):
                log_('tx check')
                return False
            return True

        # tools.log('attempt to add block: ' +str(block))
        if block_check(block):
            # tools.log('add_block: ' + str(block))
            self.db.put(block['length'], block)
            self.db.put('length', block['length'])
            self.db.put('diffLength', block['diffLength'])
            orphans = self.db.get('txs')
            self.db.put('txs', [])
            for tx in block['txs']:
                transactions.update[tx['type']](tx, True)
            for tx in orphans:
                self.add_tx(tx)




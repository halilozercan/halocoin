""" This file explains explains the rules for adding and removing blocks from the local chain.
"""
import Queue
import copy
import time

from decimal import Decimal

import custom
import pt
import tools
from ntwrk import Response

from service import Service, threaded, sync


def hex_sum(a, b):
    # Sum of numbers expressed as hexidecimal strings
    return tools.buffer_(str(hex(int(a, 16) + int(b, 16)))[2: -1], 64)


def hex_invert(n):
    # Use double-size for division, to reduce information leakage.
    return tools.buffer_(str(hex(int('f' * 128, 16) / int(n, 16)))[2: -1], 64)


class BlockchainService(Service):
    tx_types = ['spend', 'mint']

    def __init__(self, engine):
        Service.__init__(self, name='blockchain')
        self.engine = engine
        self.blocks_queue = Queue.Queue()
        self.tx_queue = Queue.Queue()
        self.db = None

    def on_register(self):
        self.db = self.engine.db
        return True

    @threaded
    def process(self):
        if not self.blocks_queue.empty():
            candidate_block = self.blocks_queue.get()
            tools.log('Received block')
            tools.log(candidate_block)
            self.add_block(candidate_block)
        elif not self.tx_queue.empty():
            candidate_tx = self.tx_queue.get()
            self.add_tx(candidate_tx)
        # Wait between each check. This way we wouldn't force CPU
        time.sleep(1)

    @sync
    def add_tx(self, tx):

        # Attempt to add a new transaction into the pool.
        # print('top of add_tx')
        out = ['']
        if not isinstance(tx, dict):
            return False

        address = tools.tx_owner_address(tx)

        # tools.log('attempt to add tx: ' +str(tx))
        txs_in_pool = self.db.get('txs')
        response = BlockchainService.tx_verify_for_pool(tx, txs_in_pool, self.db.get_account(address))
        if response.getFlag():
            txs_in_pool.append(tx)
            self.db.put('txs', txs_in_pool)
            return 'added tx in the pool: ' + str(tx)
        else:
            return 'failed to add tx because: ' + response.getData()

    @sync
    def add_block(self, block):
        """Attempts adding a new block to the blockchain.
         Median is good for weeding out liars, so long as the liars don't have 51%
         hashpower. """

        def block_check(block):

            def tx_check(txs_in_block):
                for tx in reversed(txs_in_block):
                    address_of_tx = tools.tx_owner_address(tx)
                    account_of_tx = self.db.get_account(address_of_tx)
                    if BlockchainService.tx_integrity_check(tx, txs_in_block) \
                            and tools.fee_check(tx, txs_in_block, account_of_tx):
                        continue
                    else:
                        tools.log('tx not valid')
                        return False  # Block is invalid
                return True  # Block is valid

            if not isinstance(block, dict):
                tools.log('Block is not a dict')
                return False

            if 'error' in block:
                tools.log('Errors in block')
                return False

            if not ('length' in block and isinstance(block['length'], int)):
                tools.log('Length is not valid')
                return False

            length = self.db.get('length')

            if int(block['length']) != int(length) + 1:
                tools.log('Length is not valid')
                return False

            # TODO: understand what is going on here
            if block['diffLength'] != hex_sum(self.db.get('diffLength'),
                                              hex_invert(block['target'])):
                tools.log('difflength is wrong')
                return False

            if length >= 0:
                if tools.det_hash(self.db.get(length)) != block['prevHash']:
                    tools.log('prevhash different')
                    return False

            if 'target' not in block:
                tools.log('no target in block')
                return False

            nonce_and_hash = tools.hash_without_nonce(block)
            print 'Adding block with hash\n' + tools.det_hash(nonce_and_hash)
            if tools.det_hash(nonce_and_hash) > block['target']:
                tools.log('hash is not applicable to target')
                return False

            if block['target'] != self.target(block['length']):
                tools.log('block: ' + str(block))
                tools.log('target: ' + str(self.target(block['length'])))
                tools.log('wrong target')
                return False

            #earliest = tools.median(self.recent_blockthings(self.db.get('times'),
            #                                                custom.mmm,
            #                                                self.db.get('length')))

            if 'time' not in block:
                tools.log('no time')
                return False
            if block['time'] > time.time() + 60 * 6:
                tools.log('Received block is coming from future. Call the feds')
                return False
            #if block['time'] < earliest:
            #    tools.log('Received block is generated earlier than median.')
            #    return False
            if tx_check(block['txs']):
                tools.log('Received block failed transactions check.')
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
                self.update_addresses_with_tx(tx, True)
            for tx in orphans:
                self.add_tx(tx)

    @sync
    def delete_block(self):
        """ Removes the most recent block from the blockchain. """
        length = self.db.get('length')
        if length < 0:
            return
        try:
            targets = self.db.get('targets')
            targets.pop(str(length))
            self.db.put('targets', targets)
        except:
            pass
        try:
            times = self.db.get('times')
            times.pop(str(length))
            self.db.put('times', times)
        except:
            pass

        block = self.db.get(length)
        orphans = self.db.get('txs')
        self.db.put('txs', [])

        for tx in block['txs']:
            orphans.append(tx)
            self.db.put('add_block', False)
            self.update_addresses_with_tx(tx, False)

        self.db.delete(length)
        length -= 1

        self.db.put('length', length)
        if length == -1:
            self.db.put('diffLength', '0')
        else:
            block = self.db.get(length)
            self.db.put('diffLength', block['diffLength'])

        for orphan in sorted(orphans, key=lambda x: x['count']):
            self.add_tx(orphan)

    @sync
    def recent_blockthings(self, key, size, length):

        storage = self.db.get(key)
        start = max((length - size), 0)
        end = length - max(custom.mmm, custom.history_length) - 100

        # Remove keys from storage in the range 0-end
        while end >= 0:
            if not str(end) in storage:
                break
            else:
                storage.pop(str(end))
                end -= 1

        result = []
        for i in range(start, length):
            index = str(i)
            if not index in storage:
                block_exists = self.db.exists(index)
                if not block_exists:
                    if index == self.db.get('length'):
                        self.db.put('length', i - 1)
                        block = self.db.get(index)
                # try:
                storage[index] = self.db.get(index)[key[:-1]]
                self.db.put(key, storage)
            result.append(storage[index])

        return result

    @sync
    def update_addresses_with_tx(self, tx, add_block_flag):
        if tx['type'] == 'mint':
            self.mint(tx, add_block_flag)
        elif tx['type'] == 'spend':
            self.spend(tx, add_block_flag)

    @sync
    def mint(self, tx, add_block_flag):
        print("Updating with mint tx")
        address = tools.tx_owner_address(tx)
        print("Rewarding address:" + address)
        account = self.db.get_account(address)
        if add_block_flag:
            account['amount'] += custom.block_reward
            account['count'] += 1
        else:
            account['amount'] -= custom.block_reward
            account['count'] -= 1
        self.db.put(address, account)
        print(account)

    @sync
    def spend(self, tx, add_block_flag):
        address = tools.tx_owner_address(tx)
        account = self.db.get_account(address)
        if add_block_flag:
            account['amount'] += -tx['amount']
            tx['to']['amount'] += tx['amount']
            account['amount'] += -custom.fee
            account['count'] += 1
        else:
            account['amount'] -= -tx['amount']
            tx['to']['amount'] -= tx['amount']
            account['amount'] -= -custom.fee
            account['count'] -= 1
        self.db.put(address, account)

    @staticmethod
    def sigs_match(_sigs, _pubs, msg):
        pubs = copy.deepcopy(_pubs)
        sigs = copy.deepcopy(_sigs)

        def match(sig, pubs, msg):
            for p in pubs:
                if pt.ecdsa_verify(msg, sig, p):
                    return {'bool': True, 'pub': p}
            return {'bool': False}

        for sig in sigs:
            a = match(sig, pubs, msg)
            if not a['bool']:
                return False
            sigs.remove(sig)
            pubs.remove(a['pub'])
        return True

    @staticmethod
    def tx_signature_check(tx):
        tx_copy = copy.deepcopy(tx)
        if 'signatures' not in tx or not isinstance(tx['signatures'], (list,)):
            tools.log('no signatures')
            return False
        if 'pubkeys' not in tx or not isinstance(tx['pubkeys'], (list,)):
            tools.log('no pubkeys')
            return False

        tx_copy.pop('signatures')
        if len(tx['pubkeys']) == 0:
            tools.log('pubkey error')
            return False
        if len(tx['signatures']) > len(tx['pubkeys']):
            tools.log('there are more signatures then required')
            return False

        msg = tools.det_hash(tx_copy)
        if not BlockchainService.sigs_match(copy.deepcopy(tx['signatures']),
                                            copy.deepcopy(tx['pubkeys']), msg):
            tools.log('sigs do not match')
            return False
        return True

    @staticmethod
    def tx_integrity_check(tx, txs_in_pool):
        response = Response(True, None)
        if tx['type'] == 'mint':
            response.setFlag(0 == len(filter(lambda t: t['type'] == 'mint', txs_in_pool)))
        elif tx['type'] == 'spend':
            if 'to' not in tx or not isinstance(tx['to'], (str, unicode)):
                response.setData('no to')
                response.setFlag(False)
            if not BlockchainService.tx_signature_check(tx):
                response.setData('signature check')
                response.setFlag(False)
            if len(tx['to']) <= 30:
                response.setData('that address is too short ' + 'tx: ' + str(tx))
                response.setFlag(False)
            if 'amount' not in tx or not isinstance(tx['amount'], (str, unicode)):
                response.setData('no amount')
                response.setFlag(False)
            # TODO: This is new. Check this voting transactions
            if 'vote_id' in tx:
                if not tx['to'][:-29] == '11':
                    response.setData('cannot hold votecoins in a multisig address')
                    response.setFlag(False)
            return response

    @staticmethod
    def tx_type_check(tx):
        if 'type' not in tx:
            return False
        if not isinstance(tx['type'], (str, unicode)):
            return False
        if tx['type'] not in BlockchainService.tx_types:
            return False
        return True

    @staticmethod
    def tx_verify_for_pool(tx, txs_in_pool, account):
        response = Response(True, None)
        if not BlockchainService.tx_type_check(tx):
            response.setData('type error')
            response.setFlag(False)
        if tx in txs_in_pool:
            response.setData('no duplicates')
            response.setFlag(False)
        if not BlockchainService.tx_integrity_check(tx, txs_in_pool).getFlag():
            response.setData('tx: ' + str(tx))
            response.setFlag(False)
        if tx['count'] != tools.count(account, tools.tx_owner_address(tx), txs_in_pool):
            response.setData('count error')
            response.setFlag(False)
        if not tools.fee_check(tx, txs_in_pool, account):
            response.setData('fee check error')
            response.setFlag(False)
        return response

    @sync
    def target(self, length):
        memoized_weights = [custom.inflection ** i for i in range(1000)]
        """ Returns the target difficulty at a particular blocklength. """
        if length < 4:
            return '0' * 4 + 'f' * 60  # Use same difficulty for first few blocks.

        def targetTimesFloat(target, number):
            a = int(str(target), 16)
            b = int(a * number)  # this should be rational multiplication followed by integer estimation
            return tools.buffer_(str(hex(b))[2: -1], 64)

        def multiply_things(things):
            out = 1
            while len(things) > 0:
                out = out * things[0]
                things = things[1:]
            return out

        def weights(length):  # uses float
            # returns from small to big
            out = memoized_weights[:length]
            out.reverse()
            return out

        def estimate_target():
            """
            We are actually interested in the average number of hashes required to
            mine a block. number of hashes required is inversely proportional
            to target. So we average over inverse-targets, and inverse the final
            answer. """

            def sumTargets(l):
                if len(l) < 1:
                    return 0
                while len(l) > 1:
                    l = [hex_sum(l[0], l[1])] + l[2:]
                return l[0]

            targets = self.recent_blockthings('targets', custom.history_length)
            w = weights(len(targets))  # should be rat instead of float
            tw = sum(w)
            targets = map(hex_invert, targets)

            def weighted_multiply(i):
                return targetTimesFloat(targets[i], w[i] / tw)  # this should use rat division instead

            weighted_targets = [weighted_multiply(i) for i in range(len(targets))]
            return hex_invert(sumTargets(weighted_targets))

        def estimate_time():
            times = self.recent_blockthings('times', custom.history_length)
            times = map(Decimal, times)
            block_lengths = [times[i] - times[i - 1] for i in range(1, len(times))]
            w = weights(len(block_lengths))  # Geometric weighting
            tw = sum(w)
            return sum([w[i] * block_lengths[i] / tw for i in range(len(block_lengths))])

        retarget = estimate_time() / custom.blocktime
        return targetTimesFloat(estimate_target(), retarget)


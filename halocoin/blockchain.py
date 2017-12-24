import copy
import queue
import time
from cdecimal import Decimal

from halocoin import custom, api
from halocoin import tools
from halocoin.ntwrk import Response
from halocoin.service import Service, threaded, sync, NoExceptionQueue


class BlockchainService(Service):
    """
    tx_types are allowed transactions in coinami platform.
    spend: Send coins from one address to another
    mint: Traditional mining coinbase
    reward: Reward coins sent from an authority to an address
    auth_reg: Authority register. Includes a certificate that proves this authority is approved by root.
    job_dump: Announcing jobs that are prepared and ready to be downloaded
    job_request: Entering a pool for a job request.
    """
    tx_types = ['spend', 'mint', 'reward', 'auth_reg', 'job_dump', 'job_request']
    IDLE = 1
    SYNCING = 2

    def __init__(self, engine):
        Service.__init__(self, name='blockchain')
        self.engine = engine
        self.blocks_queue = NoExceptionQueue(3)
        self.tx_queue = NoExceptionQueue(100)
        self.db = None
        self.account = None
        self.clientdb = None
        self.in_memory_db = {}
        self.__state = BlockchainService.IDLE

    def on_register(self):
        self.db = self.engine.db
        self.account = self.engine.account
        self.clientdb = self.engine.clientdb
        print("Started Blockchain")
        return True

    @threaded
    def process_blocks(self):
        """
        In this thread we check blocks queue for possible additions to blockchain.
        Following type is expected to come out of the queue. Any other type will be rejected.
        ([candidate_blocks in order], peer_node_id)
        Only 3 services actually put stuff in queue: peer_listen, peer_check, miner
        PeerListen and PeerCheck obeys the expected style.
        Miner instead puts one block in candidate block list, node id is 'miner'
        :return:
        """
        try:
            candidate = self.blocks_queue.get(timeout=1)
        except queue.Empty:
            return
        self.set_chain_state(BlockchainService.SYNCING)
        try:
            if isinstance(candidate, tuple):
                blocks = candidate[0]
                node_id = candidate[1]
                total_number_of_blocks_added = 0

                for block in blocks:
                    if not BlockchainService.single_block_integrity_check(block) and node_id != 'miner':
                        self.peer_reported_false_blocks(node_id)
                        raise Exception('Peer {} reported false blocks'.format(node_id))

                for block in blocks:
                    add_block_result = self.add_block(block)
                    if add_block_result == 2:  # A block that is ahead of us could not be added. No need to proceed.
                        break
                    elif add_block_result == 0:
                        total_number_of_blocks_added += 1

                length = self.db.get('length')
                for i in range(20):
                    block = self.db.get(length)
                    if BlockchainService.fork_check(blocks, length, block):
                        self.delete_block()
                        length -= 1
                    else:
                        break

                if total_number_of_blocks_added == 0:
                    # All received blocks failed. Punish the peer by lowering rank.
                    self.peer_reported_false_blocks(node_id)
                else:
                    api.new_block()
        except Exception as e:
            tools.log(e)
        self.set_chain_state(BlockchainService.IDLE)
        self.blocks_queue.task_done()

    @threaded
    def process_txs(self):
        try:
            candidate_tx = self.tx_queue.get(timeout=1)
        except queue.Empty:
            return
        self.add_tx(candidate_tx)
        self.tx_queue.task_done()

    @sync
    def set_chain_state(self, new_state):
        self.__state = new_state

    @sync
    def get_chain_state(self):
        return self.__state

    @sync
    def tx_pool(self):
        """
        Return all the transactions waiting in the pool.
        This method should be used instead of direct access to db
        :return:
        """
        return self.db.get('txs')

    @sync
    def tx_pool_add(self, tx):
        """
        This is an atomic add operation for txs pool.
        :param tx: Transaction to be added
        :return: None
        """
        txs = self.db.get('txs')
        txs.append(tx)
        self.db.put('txs', txs)
        api.new_tx_in_pool()

    @sync
    def tx_pool_pop_all(self):
        """
        Atomic operation to pop everything
        :return: transactions list
        """
        txs = self.db.get('txs')
        self.db.put('txs', [])
        api.new_tx_in_pool()
        return txs

    @sync
    def peer_reported_false_blocks(self, node_id):
        peer = self.clientdb.get_peer(node_id)
        peer['rank'] *= 0.8
        peer['rank'] += 0.2 * 30
        self.clientdb.update_peer(peer)

    def add_tx(self, tx):

        if not isinstance(tx, dict):
            return Response(False, 'Transactions must be dict typed')

        txs_in_pool = self.tx_pool()

        if tx in txs_in_pool:
            return Response(False, 'no duplicates')
        if 'type' not in tx or tx['type'] not in BlockchainService.tx_types or tx['type'] == 'mint':
            return Response(False, 'Invalid type')
        integrity_check = self.tx_integrity_check(tx)
        if not integrity_check.getFlag():
            return Response(False, 'Transaction failed integrity check: ' + integrity_check.getData())
        if not self.account.check_tx_validity_to_blockchain(tx):
            return Response(False, 'Transaction failed current state check')

        self.tx_pool_add(tx)
        return Response(True, 'Added tx into the pool: ' + str(tx))

    def add_block(self, block):
        """Attempts adding a new block to the blockchain.
         Median is good for weeding out liars, so long as the liars don't have 51%
         hashpower. """

        length = self.db.get('length')

        if int(block['length']) < int(length) + 1:
            return 1
        elif int(block['length']) > int(length) + 1:
            return 2

        if (length >= 0 and block['diffLength'] != tools.hex_sum(self.db.get('diffLength'), tools.hex_invert(block['target']))) \
                or (length < 0 and block['diffLength'] != tools.hex_invert(block['target'])):
            tools.log(block['diffLength'])
            tools.log(tools.hex_sum(self.db.get('diffLength'), tools.hex_invert(block['target'])))
            tools.log(block['length'])
            tools.log('difflength is wrong')
            return 3

        if length >= 0 and tools.det_hash(self.db.get(length)) != block['prevHash']:
            tools.log('prevhash different')
            return 3

        nonce_and_hash = tools.hash_without_nonce(block)
        if tools.det_hash(nonce_and_hash) > block['target']:
            tools.log('hash value does not match the target')
            return 3

        if block['target'] != self.target(block['length']):
            tools.log('block: ' + str(block))
            tools.log('target: ' + str(self.target(block['length'])))
            tools.log('wrong target')
            return 3

        recent_time_values = self.recent_blockthings('times', custom.median_block_time_limit)
        median_block = tools.median(recent_time_values)
        if block['time'] < median_block:
            tools.log('Received block is generated earlier than median.')
            return 3

        # Check that block includes exactly one mint transaction
        if 'txs' not in block:
            tools.log('Received block does not include txs. At least a coinbase tx must be present')
            return 3

        # Sum of all mint type transactions must be one
        mint_present = sum([0 if tx['type'] != 'mint' else 1 for tx in block['txs']])
        if mint_present != 1:
            tools.log('Received block includes wrong amount of mint txs')
            return 3

        # TODO: Add tx integrity check for all tx types
        flag = True
        for tx in block['txs']:
            flag &= self.tx_integrity_check(tx).getFlag()
            flag &= self.account.check_tx_validity_to_blockchain(tx)
        if not flag:
            tools.log('Received block failed special txs check.')
            return 3

        self.db.put(block['length'], block)
        self.db.put('length', block['length'])
        self.db.put('diffLength', block['diffLength'])

        orphans = self.tx_pool_pop_all()

        self.account.update_database_with_block(block)

        for orphan in sorted(orphans, key=lambda x: x['count']):
            self.add_tx(orphan)

        return 0

    def delete_block(self):
        """ Removes the most recent block from the blockchain. """
        length = self.db.get('length')
        if length < 0:
            return

        targets = self.db.get('targets')
        if str(length) in targets:
            targets.pop(str(length))
        self.db.put('targets', targets)

        times = self.db.get('times')
        if str(length) in times:
            times.pop(str(length))
        self.db.put('times', times)

        block = self.db.get(length)
        self.account.rollback_block(block)

        orphans = self.tx_pool_pop_all()

        for tx in block['txs']:
            orphans.append(tx)

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

        return True

    @staticmethod
    def single_block_integrity_check(block):
        if not isinstance(block, dict):
            tools.log('Block is not a dict')
            return False

        if not ('length' in block and isinstance(block['length'], int)):
            return False

        if 'version' not in block or block['version'] != custom.version:
            return False

        if 'target' not in block:
            tools.log('no target in block')
            return False

        if 'time' not in block:
            tools.log('no time')
            return False

        if block['time'] > time.time() + 60 * 6:
            tools.log('Received block is coming from the future. Call the feds')
            return False

        return True

    def recent_blockthings(self, key, size, length=0, blocks=None):
        """
        Legacy of zack-bitcoin. This is the true art of naming of functions.
        """
        if length == 0:
            length = self.db.get('length')

        if key in self.in_memory_db:
            storage = self.in_memory_db[key]
        else:
            storage = self.db.get(key)
        start = max((length - size), 0)
        result = []
        for i in range(start, length):
            leng = str(i)
            if not leng in storage:
                storage[leng] = self.db.get(leng)[key[:-1]]  # Remove last character that is 's' e.g. targets => target
            result.append(storage[leng])
        self.in_memory_db[key] = storage
        self.db.put(key, storage)
        return result

    @staticmethod
    def sigs_match(_sigs, _pubs, msg):
        pubs = copy.deepcopy(_pubs)
        sigs = copy.deepcopy(_sigs)

        def match(sig, pubs, msg):
            for p in pubs:
                if tools.signature_verify(msg, sig, p):
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
        if len(tx['pubkeys']) == 0:
            tools.log('pubkey error')
            return False
        if len(tx['signatures']) > len(tx['pubkeys']):
            tools.log('there are more signatures than required')
            return False

        tx_copy.pop('signatures')
        msg = tools.det_hash(tx_copy)
        if not BlockchainService.sigs_match(copy.deepcopy(tx['signatures']),
                                            copy.deepcopy(tx['pubkeys']), msg):
            tools.log('sigs do not match')
            return False
        return True

    @staticmethod
    def fork_check(newblocks, length, top_block_on_chain):
        """
        Check whether a fork happens while adding these blocks.
        If a fork is detected, return the index of last matched block.
        :param newblocks: Received blocks.
        :param length:
        :param top_block_on_chain:
        :return:
        """
        recent_hash = tools.det_hash(top_block_on_chain)
        their_hashes = list(map(lambda x: x['prevHash'] if x['length'] > 0 else 0, newblocks))
        their_hashes += [tools.det_hash(newblocks[-1])]
        b = (recent_hash not in their_hashes) and newblocks[0]['length'] - 1 < length < newblocks[-1]['length']
        return b

    def tx_integrity_check(self, tx):
        """
        This functions test whether a transaction has basic things right.
        Does it have amount, recipient, RIGHT SIGNATURES and correct address types.
        :param tx:
        :return:
        """

        if tx['type'] == 'spend' or tx['type'] == 'reward':
            if 'to' not in tx or not isinstance(tx['to'], str):
                return Response(False, 'Reward or spend transactions must be addressed')
            if not BlockchainService.tx_signature_check(tx):
                return Response(False, 'Transaction is not properly signed')
            if len(tx['to']) <= 30:
                return Response(False, 'Address is not valid')
            if 'amount' not in tx or not isinstance(tx['amount'], int):
                return Response(False, 'Transaction amount is not given or not a proper integer')

        if tx['type'] == 'job_request':
            if 'job_id' not in tx:
                return Response(False, 'Job id missing from the request')
            elif 'amount' not in tx:
                return Response(False, 'Bidding amount is missing from the request')

        if tx['type'] == 'reward':
            if 'auth' not in tx:
                return Response(False, 'Reward transactions must include auth name')
            cert = self.account.find_certificate_by_name(tx['auth'])
            if cert is None:
                return Response(False, 'given auth name does not have a known certificate')
            if tx['pubkeys'] != [tools.get_pubkey_from_certificate(cert).to_string()]:
                return Response(False, 'pubkeys do not match with known pubkeys of auth')
            if 'job_id' not in tx:
                return Response(False, 'Reward must be addressed to a job id')

        if tx['type'] == 'job_dump':
            if 'auth' not in tx:
                return Response(False, 'Job dump transactions must include auth name')
            cert = self.account.find_certificate_by_name(tx['auth'])
            if cert is None:
                return Response(False, 'given auth name does not have a known certificate')
            elif tx['pubkeys'] != [tools.get_pubkey_from_certificate(cert).to_string()]:
                return Response(False, 'pubkeys do not match with known pubkeys of auth')
            if 'job' not in tx or not isinstance(tx['job'], dict) or \
                            'id' not in tx['job'] or 'timestamp' not in tx['job']:
                return Response(False, 'Job dump transactions must include a job in it. Makes sense right?')
            if 'max_amount' not in tx['job'] or 'min_amount' not in tx['job']:
                return Response(False, 'Job dump transactions must specify maximum and minimum allowed rewards')

        if tx['type'] == 'auth_reg':
            if 'certificate' not in tx:
                return Response(False, 'Auth must register with a valid certificate')
            elif tx['pubkeys'] != [tools.get_pubkey_from_certificate(tx['certificate']).to_string()]:
                return Response(False, 'pubkeys do not match with certificate')
        return Response(True, 'Everything seems fine')

    def target(self, length, blocks=None):
        def targetTimesFloat(target, number):
            a = int(str(target), 16)
            b = int(a * number)  # this should be rational multiplication followed by integer estimation
            return tools.buffer_(format(b, 'x'), 64)

        def weights(length):  # uses float
            # returns from small to big
            out = custom.memoized_weights[:length]
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
                    l = [tools.hex_sum(l[0], l[1])] + l[2:]
                return l[0]

            targets = self.recent_blockthings('targets', custom.history_length, blocks=blocks)
            w = weights(len(targets))  # should be rat instead of float
            tw = sum(w)
            targets = list(map(tools.hex_invert, targets))

            weighted_targets = [targetTimesFloat(targets[i], w[i] / tw) for i in range(len(targets))]
            return tools.hex_invert(sumTargets(weighted_targets))

        def estimate_time():
            times = self.recent_blockthings('times', custom.history_length, blocks=blocks)
            times = list(map(Decimal, times))
            # How long it took to generate blocks
            block_times = [times[i] - times[i - 1] for i in range(1, len(times))]
            w = weights(len(block_times))  # Geometric weighting
            tw = sum(w)
            return sum([w[i] * block_times[i] / tw for i in range(len(block_times))])

        """ Returns the target difficulty at a particular blocklength. """
        if length < 100:
            return bytearray.fromhex('0' * 4 + 'f' * 60)  # Use same difficulty for first few blocks.
        if length == 100 or length % custom.recalculate_target_at == 0:
            retarget = estimate_time() / custom.blocktime
            result = targetTimesFloat(estimate_target(), retarget)
            return bytearray.fromhex(result)
        elif 100 < length < custom.recalculate_target_at:
            return self.db.get(100)['target']
        else:
            last_block = length - (length % custom.recalculate_target_at)
            return self.db.get(last_block)['target']


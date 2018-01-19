import copy
import queue
import threading
import time
from cdecimal import Decimal

import yaml

from halocoin import custom, api, service
from halocoin import tools
from halocoin.ntwrk import Response
from halocoin.service import Service, threaded, sync, NoExceptionQueue, lockit


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
    tx_types = ['spend', 'mint', 'reward', 'auth_reg', 'job_dump', 'deposit', 'withdraw']
    IDLE = 1
    SYNCING = 2

    def __init__(self, engine):
        Service.__init__(self, name='blockchain')
        self.engine = engine
        self.blocks_queue = NoExceptionQueue(3)
        self.tx_queue = NoExceptionQueue(100)
        self.db = None
        self.statedb = None
        self.clientdb = None
        self.__state = BlockchainService.IDLE
        self.addLock = threading.RLock()

    def on_register(self):
        self.db = self.engine.db
        self.statedb = self.engine.statedb
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
            self.set_chain_state(BlockchainService.SYNCING)
            try:
                if isinstance(candidate, tuple):
                    blocks = candidate[0]
                    node_id = candidate[1]
                    total_number_of_blocks_added = 0

                    for block in blocks:
                        if not BlockchainService.block_integrity_check(block) and node_id != 'miner':
                            self.peer_reported_false_blocks(node_id)
                            raise Exception('Peer {} reported false blocks'.format(node_id))

                    self.db.simulate()
                    length = self.db.get('length')
                    for i in range(20):
                        block = self.get_block(length)
                        if self.fork_check(blocks, length, block):
                            self.delete_block()
                            length -= 1
                        else:
                            break

                    for block in blocks:
                        add_block_result = self.add_block(block)
                        if add_block_result == 2:  # A block that is ahead of us could not be added. No need to proceed.
                            break
                        elif add_block_result == 0:
                            total_number_of_blocks_added += 1

                    if total_number_of_blocks_added == 0 or self.db.get('length') != blocks[-1]['length']:
                        # All received blocks failed. Punish the peer by lowering rank.
                        self.db.rollback()
                        if node_id != 'miner':
                            self.peer_reported_false_blocks(node_id)
                    else:
                        self.db.commit()
                        api.new_block()
            except Exception as e:
                tools.log(e)
            self.set_chain_state(BlockchainService.IDLE)
            self.blocks_queue.task_done()
        except queue.Empty:
            pass

        try:
            candidate_tx = self.tx_queue.get(timeout=1)
            self.add_tx(candidate_tx)
        except queue.Empty:
            return
        except service.LockException as e:
            tools.log(e)
        self.tx_queue.task_done()

    @sync
    def set_chain_state(self, new_state):
        self.__state = new_state

    @sync
    def get_chain_state(self):
        return self.__state

    @lockit('tx_pool')
    def tx_pool(self):
        """
        Return all the transactions waiting in the pool.
        This method should be used instead of direct access to db
        :return:
        """
        return self.db.get('txs')

    @lockit('tx_pool')
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

    @lockit('tx_pool')
    def tx_pool_pop_all(self):
        """
        Atomic operation to pop everything
        :return: transactions list
        """
        txs = self.db.get('txs')
        self.db.put('txs', [])
        api.new_tx_in_pool()
        return txs

    def peer_reported_false_blocks(self, node_id):
        peer = self.clientdb.get_peer(node_id)
        peer['rank'] *= 0.8
        peer['rank'] += 0.2 * 30
        self.clientdb.update_peer(peer)

    @lockit('blockchain', timeout=2)
    def add_tx(self, tx):
        if not isinstance(tx, dict):
            return Response(False, 'Transactions must be dict typed')

        txs_in_pool = self.tx_pool()

        if tx in txs_in_pool:
            return Response(False, 'no duplicates')
        if 'type' not in tx or tx['type'] not in BlockchainService.tx_types or tx['type'] == 'mint':
            return Response(False, 'Invalid type')
        integrity_check = BlockchainService.tx_integrity_check(tx)
        if not integrity_check.getFlag():
            return Response(False, 'Transaction failed integrity check: ' + integrity_check.getData())
        self.db.simulate()
        block = {
            'length': self.db.get('length') + 1,
            'txs': self.tx_pool() + [tx]
        }
        current_state_check = self.statedb.update_database_with_block(block)
        self.db.rollback()
        if not current_state_check:
            return Response(False, 'Transaction failed current state check')

        self.tx_pool_add(tx)
        return Response(True, 'Added tx into the pool: ' + str(tx))

    @lockit('blockchain')
    def add_block(self, block):
        """Attempts adding a new block to the blockchain.
         Median is good for weeding out liars, so long as the liars don't have 51%
         hashpower. """

        length = self.db.get('length')
        block_at_length = self.get_block(length)

        if int(block['length']) < int(length) + 1:
            return 1
        elif int(block['length']) > int(length) + 1:
            return 2

        tools.echo('add block')

        if (length >= 0 and block['diffLength'] != tools.hex_sum(block_at_length['diffLength'],
                                                                 tools.hex_invert(block['target']))) \
                or (length < 0 and block['diffLength'] != tools.hex_invert(block['target'])):
            tools.log(block['diffLength'])
            tools.log(tools.hex_sum(self.db.get('diffLength'), tools.hex_invert(block['target'])))
            tools.log(block['length'])
            tools.log('difflength is wrong')
            return 3

        if length >= 0 and tools.det_hash(block_at_length) != block['prevHash']:
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

        """
        recent_time_values = self.recent_blockthings('times', custom.median_block_time_limit)
        median_block = tools.median(recent_time_values)
        if block['time'] < median_block:
            tools.log('Received block is generated earlier than median.')
            return 3
        """

        # Check that block includes exactly one mint transaction
        if 'txs' not in block:
            tools.log('Received block does not include txs. At least a coinbase tx must be present')
            return 3

        # Sum of all mint type transactions must be one
        mint_present = sum([0 if tx['type'] != 'mint' else 1 for tx in block['txs']])
        if mint_present != 1:
            tools.log('Received block includes wrong amount of mint txs')
            return 3

        flag = True
        for tx in block['txs']:
            flag &= BlockchainService.tx_integrity_check(tx).getFlag()
        if not flag:
            tools.log('Received block failed special txs check.')
            return 3

        if not self.statedb.update_database_with_block(block):
            return 3

        self.put_block(block['length'], block)
        self.db.put('length', block['length'])
        self.db.put('diffLength', block['diffLength'])

        orphans = self.tx_pool_pop_all()

        for orphan in sorted(orphans, key=lambda x: x['count'] if 'count' in x else -1):
            self.tx_queue.put(orphan)

        tools.techo('add block')
        return 0

    def delete_block(self):
        length = self.db.get('length')
        if length < 0:
            return

        block = self.get_block(length)
        self.statedb.rollback_block(block)

        orphans = self.tx_pool_pop_all()

        for tx in block['txs']:
            orphans.append(tx)

        self.del_block(length)
        length -= 1

        self.db.put('length', length)
        if length == -1:
            self.db.put('diffLength', '0')
        else:
            block = self.get_block(length)
            self.db.put('diffLength', block['diffLength'])

        for orphan in sorted(orphans, key=lambda x: x['count']):
            self.tx_queue.put(orphan)

        return True

    @lockit('blockchain')
    def get_block(self, length):
        length = str(length).zfill(12)
        return self.db.get('block_' + length)

    @lockit('blockchain')
    def put_block(self, length, block):
        length = str(length).zfill(12)
        return self.db.put('block_' + length, block)

    @lockit('blockchain')
    def del_block(self, length):
        length = str(length).zfill(12)
        return self.db.delete('block_' + length)

    @staticmethod
    def block_integrity_check(block):
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

    def fork_check(self, newblocks, length, top_block_on_chain):
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
        a = (recent_hash not in their_hashes)
        b = newblocks[0]['length'] - 1 < length < newblocks[-1]['length']
        c = tools.det_hash(newblocks[0]) == tools.det_hash(self.get_block(newblocks[0]['length']))
        return a and b and c

    @staticmethod
    def tx_integrity_check(tx):
        """
        This functions test whether a transaction has basic things right.
        Does it have amount, recipient, RIGHT SIGNATURES and correct address types.
        :param tx:
        :return:
        """
        if not isinstance(tx, dict):
            return Response(False, 'Transaction is not a proper python dict')

        if tx['version'] != custom.version:
            return Response(False, 'belongs to an earlier version')

        if tx['type'] == 'spend':
            if 'to' not in tx or not isinstance(tx['to'], str):
                return Response(False, 'Reward or spend transactions must be addressed')
            if not BlockchainService.tx_signature_check(tx):
                return Response(False, 'Transaction is not properly signed')
            if len(tx['to']) <= 30:
                return Response(False, 'Address is not valid')
            if 'amount' not in tx or not isinstance(tx['amount'], int):
                return Response(False, 'Transaction amount is not given or not a proper integer')
            if 'count' not in tx or not isinstance(tx['count'], int):
                return Response(False, 'transaction count is missing')
        elif tx['type'] == 'reward':
            if not BlockchainService.tx_signature_check(tx):
                return Response(False, 'Transaction is not properly signed')
            if 'auth' not in tx:
                return Response(False, 'Reward transactions must include auth name')
            if 'job_id' not in tx:
                return Response(False, 'Reward must be addressed to a job id')
            if 'to' not in tx or not tools.is_address_valid(tx['to']):
                return Response(False, 'There must be a receiver of the reward.')
        # TODO: Add signature check for authority transactions
        elif tx['type'] == 'auth_reg':
            if 'certificate' not in tx:
                return Response(False, 'Auth must register with a valid certificate')
            elif tx['pubkeys'] != [tools.get_pubkey_from_certificate(tx['certificate']).to_string()]:
                return Response(False, 'pubkeys do not match with certificate')
            elif 'host' not in tx or not isinstance(tx['host'], str):
                return Response(False, 'Authorities require to provide a hosting address')
            elif 'supply' not in tx or not isinstance(tx['supply'], int):
                return Response(False, 'Initial supply is not found')
        elif tx['type'] == 'job_dump':
            if 'auth' not in tx:
                return Response(False, 'Job dump transactions must include auth name')
            if 'job' not in tx or not isinstance(tx['job'], dict) or \
                            'id' not in tx['job'] or 'timestamp' not in tx['job']:
                return Response(False, 'Job dump transactions must include a job in it. Makes sense right?')
            if 'amount' not in tx['job']:
                return Response(False, 'Job dump transactions must specify the reward')
        elif tx['type'] == 'deposit' or tx['type'] == 'withdraw':
            if not BlockchainService.tx_signature_check(tx):
                return Response(False, 'Transaction is not properly signed')
            if 'amount' not in tx or not isinstance(tx['amount'], int):
                return Response(False, 'Transaction amount is not given or not a proper integer')
            if 'count' not in tx or not isinstance(tx['count'], int):
                return Response(False, 'transaction count is missing')

        return Response(True, 'Everything seems fine')

    def recent_block_attributes(self, key, size):
        length = self.db.get('length')
        start = max((length - size), 0)
        result = []
        start_key = ('block_' + str(start).zfill(12)).encode()
        stop_key = ('block_' + str(length).zfill(12)).encode()
        blocks = list(self.db.iterator(start=start_key, stop=stop_key, include_stop=False))
        for _key, value in blocks:
            value = yaml.load(value.decode())
            result.append(value[key[:-1]])
        return result

    def target(self, length):
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

            targets = self.recent_block_attributes('targets', custom.history_length)
            w = weights(len(targets))  # should be rat instead of float
            tw = sum(w)
            targets = list(map(tools.hex_invert, targets))

            weighted_targets = [targetTimesFloat(targets[i], w[i] / tw) for i in range(len(targets))]
            return tools.hex_invert(sumTargets(weighted_targets))

        def estimate_time():
            times = self.recent_block_attributes('times', custom.history_length)
            times = list(map(Decimal, times))
            # How long it took to generate blocks
            block_times = [times[i] - times[i - 1] for i in range(1, len(times))]
            w = weights(len(block_times))  # Geometric weighting
            tw = sum(w)
            return sum([w[i] * block_times[i] / tw for i in range(len(block_times))])

        """ Returns the target difficulty at a particular blocklength. """
        if length < 100:
            return bytearray.fromhex(custom.first_target)  # Use same difficulty for first few blocks.
        if length == 100 or length % custom.recalculate_target_at == 0:
            retarget = estimate_time() / custom.blocktime
            result = targetTimesFloat(estimate_target(), retarget)
            return bytearray.fromhex(result)
        elif 100 < length < custom.recalculate_target_at:
            return self.get_block(100)['target']
        else:
            last_block = length - (length % custom.recalculate_target_at)
            return self.get_block(last_block)['target']

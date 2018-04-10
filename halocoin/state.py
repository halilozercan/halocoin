import copy

from halocoin import tools, custom
from halocoin.ntwrk import Response
from halocoin.service import lockit


class StateDatabase:
    """
    StateDatabase is where we evaluate and store the current state of blockchain.
    User accounts referring addresses, jobs, authorities and many more are stored here.
    State change can be triggered by only adding or removing a block.
    A state can be simulated against a transaction, multiple transactions or blocks.
    These simulations can be recorded or removed upon the result of simulation.
    Simulations are basically not committed database changes.
    """
    default_account = {
        'amount': 0,
        'count': 0,
        'tx_blocks': set()
    }

    def __init__(self, engine):
        self.engine = engine
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

    @lockit('kvstore')
    def get_account(self, address):
        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(StateDatabase.default_account)
        account['address'] = copy.deepcopy(address)
        return account

    def update_account(self, address, new_account):
        if new_account['amount'] < 0:
            return False
        self.db.put(address, new_account)
        return True

    def update_database_with_tx(self, tx, block_length):
        send_address = tools.tx_owner_address(tx)
        send_account = self.get_account(send_address)

        if tx['type'] == 'mint':
            send_account['amount'] += tools.block_reward(block_length)
            self.update_account(send_address, send_account)
        elif tx['type'] == 'spend':
            if tx['count'] < self.known_tx_count(send_address):
                return Response(False, "Transaction count mismatch")

            recv_address = tx['to']
            recv_account = self.get_account(recv_address)

            send_account['amount'] -= tx['amount']
            send_account['count'] = (tx['count'] + 1)
            send_account['tx_blocks'].add(block_length)

            recv_account['amount'] += tx['amount']
            recv_account['tx_blocks'].add(block_length)

            if (recv_account['amount'] < 0) or (send_account['amount'] < 0):
                return Response(False, "Not sufficient funds in the account")

            self.update_account(send_address, send_account)
            self.update_account(recv_address, recv_account)
        else:
            return Response(False, "Transaction type is not defined")
        return Response(True, "Fine!")

    def update_database_with_block(self, block):
        """
        This method should only be called after block passes every check.

        :param block:
        :return: Whether it was a successfull add operation
        """

        txs = sorted(block['txs'], key=lambda x: x['count'] if 'count' in x else -1)

        for tx in txs:
            result = self.update_database_with_tx(tx, block['length'])
            if not result:
                return False

        return True

    def get_valid_txs_for_next_block(self, txs, new_length):
        txs = sorted(txs, key=lambda x: x['count'] if 'count' in x else -1)
        valid_txs = []
        self.db.simulate()
        for tx in txs:
            result = self.update_database_with_tx(tx, new_length)
            if result:
                valid_txs.append(tx)
        self.db.rollback()
        return valid_txs

    def rollback_block(self, block):
        """
        A block rollback means removing the block from chain.
        A block is defined by its transactions. Here we rollback every object in database to the version
        that existed before this block. Blocks must be removed one by one.

        :param block: Block to be removed
        :return: Success of removal
        """
        current_length = self.db.get('length')
        if block['length'] != current_length:
            # Block is not at the top the chain
            return False

        if not self.db.exists('changes_' + str(block['length'])):
            tools.log('Cannot delete a block because transaction index is missing')
            return False

        changes = self.db.get('changes_' + str(block['length']))
        for key, value in changes.items():
            self.db.put(key, value['old'])

        self.db.delete('changes_' + str(block['length']))
        tools.log('Successfully removed block %d' % block['length'])

    @lockit('kvstore')
    def known_tx_count(self, address, count_pool=False):
        # Returns the number of transactions that pubkey has broadcast.
        def highest_order_unconfirmed_tx(_address):
            # Find the transactions that include 'count', broadcasted from _address
            txs = list(filter(lambda t: _address == tools.tx_owner_address(t) and 'count' in t, txs_in_pool))
            if len(txs) > 0:
                tx = max(txs, key=lambda t: t['count'])
                return tx['count']
            else:
                return -1

        account = self.get_account(address)
        if count_pool:
            txs_in_pool = self.blockchain.tx_pool()
            pool_winner = highest_order_unconfirmed_tx(address) + 1
            if account['count'] < pool_winner:
                account['count'] = pool_winner
        return account['count']

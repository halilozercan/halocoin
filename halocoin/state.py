import copy

from halocoin import tools
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
        'cache-length': -1,
        'tx_blocks': []
    }

    def __init__(self, engine):
        self.engine = engine
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

    @lockit('kvstore')
    def get_account(self, address, apply_tx_pool=False):
        def update_account_with_txs(address, account, txs):
            for tx in txs:
                owner = tools.tx_owner_address(tx)
                if tx['type'] == 'spend':
                    if owner == address:
                        account['amount'] -= tx['amount']
                    if tx['to'] == address:
                        account['amount'] += tx['amount']

            return account

        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(StateDatabase.default_account)

        if apply_tx_pool:
            txs = self.blockchain.tx_pool()
            account = update_account_with_txs(address, account, txs)

        if 'tx_blocks' not in account:
            account['tx_blocks'] = []

        return account

    @lockit('kvstore')
    def remove_account(self, address):
        self.db.delete(address)
        return True

    def update_account(self, address, new_account):
        if new_account['amount'] < 0:
            return False
        self.db.put(address, new_account)
        return True

    def update_database_with_tx(self, tx, block_length, count_pool=False):
        send_address = tools.tx_owner_address(tx)
        send_account = self.get_account(send_address)

        if tx['type'] == 'mint':
            send_account['amount'] += tools.block_reward(block_length)
            self.update_account(send_address, send_account)
        elif tx['type'] == 'spend':
            if tx['count'] != self.known_tx_count(send_address, count_pool=count_pool):
                return False

            recv_address = tx['to']
            recv_account = self.get_account(recv_address)

            send_account['amount'] -= tx['amount']
            send_account['count'] += 1
            send_account['tx_blocks'].append(block_length)

            recv_account['amount'] += tx['amount']
            recv_account['tx_blocks'].append(block_length)

            if (recv_account['amount'] < 0) or (send_account['amount'] < 0):
                return False

            self.update_account(send_address, send_account)
            self.update_account(recv_address, recv_account)
        else:
            return False
        return True

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
        # TODO: 0.007-12c changes
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

        for tx in block['txs']:
            tx_owner_address = tools.tx_owner_address(tx)
            owner_account = self.get_account(tx_owner_address)
            if tx['type'] == 'mint':
                owner_account['amount'] -= tools.block_reward(block['length'])
                self.db.put(tx_owner_address, owner_account)
            elif tx['type'] == 'spend':
                owner_account['amount'] += tx['amount']
                owner_account['count'] -= 1
                owner_account['tx_blocks'].remove(block['length'])

                receiver_account = self.db.get(tx['to'])
                receiver_account['amount'] -= tx['amount']
                receiver_account['tx_blocks'].remove(block['length'])

                self.db.put(tx_owner_address, owner_account)
                self.db.put(tx['to'], receiver_account)

    @lockit('kvstore')
    def known_tx_count(self, address, count_pool=True, txs_in_pool=None):
        # Returns the number of transactions that pubkey has broadcast.
        def number_of_unconfirmed_txs(_address):
            return len(list(filter(lambda t: _address == tools.tx_owner_address(t), txs_in_pool)))

        account = self.get_account(address)
        surplus = 0
        if count_pool:
            txs_in_pool = self.blockchain.tx_pool()
            surplus += number_of_unconfirmed_txs(address)
        return account['count'] + surplus